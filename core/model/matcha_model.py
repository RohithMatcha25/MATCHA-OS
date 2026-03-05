"""
MATCHA AI Model — Custom Language Model
Built from scratch on top of a transformer architecture.
Fine-tuned to MATCHA's personality, knowledge, and behaviour.

Architecture: Lightweight transformer (GPT-style)
- Small enough to run on any laptop (CPU-only)
- Fine-tuned on MATCHA-specific conversation data
- Learns from user interactions over time
"""

import os
import json
import math
import torch
import torch.nn as nn
from pathlib import Path
from datetime import datetime

MODEL_DIR = Path(__file__).parent / "weights"
TRAINING_DATA = Path(__file__).parent / "training_data.json"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ── Transformer Architecture ──────────────────────────────────────────────────

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, num_heads):
        super().__init__()
        assert d_model % num_heads == 0
        self.d_model = d_model
        self.num_heads = num_heads
        self.d_k = d_model // num_heads
        self.W_q = nn.Linear(d_model, d_model)
        self.W_k = nn.Linear(d_model, d_model)
        self.W_v = nn.Linear(d_model, d_model)
        self.W_o = nn.Linear(d_model, d_model)

    def forward(self, x, mask=None):
        B, T, C = x.shape
        Q = self.W_q(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        K = self.W_k(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        V = self.W_v(x).view(B, T, self.num_heads, self.d_k).transpose(1, 2)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / math.sqrt(self.d_k)
        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)
        attn = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn, V).transpose(1, 2).contiguous().view(B, T, C)
        return self.W_o(out)


class FeedForward(nn.Module):
    def __init__(self, d_model, d_ff, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(self, x):
        return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(d_model, num_heads)
        self.ff = FeedForward(d_model, d_ff, dropout)
        self.ln1 = nn.LayerNorm(d_model)
        self.ln2 = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        x = x + self.dropout(self.attn(self.ln1(x), mask))
        x = x + self.dropout(self.ff(self.ln2(x)))
        return x


class MatchaLM(nn.Module):
    """
    MATCHA Language Model
    Lightweight GPT-style transformer, designed to run on CPU.
    ~10M parameters — fits on any laptop.
    """

    def __init__(self, vocab_size, d_model=256, num_heads=8,
                 num_layers=6, d_ff=1024, max_seq=512, dropout=0.1):
        super().__init__()
        self.d_model = d_model
        self.max_seq = max_seq
        self.token_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_seq, d_model)
        self.dropout = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            TransformerBlock(d_model, num_heads, d_ff, dropout)
            for _ in range(num_layers)
        ])
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        # Weight tying
        self.head.weight = self.token_emb.weight
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, x, targets=None):
        B, T = x.shape
        pos = torch.arange(T, device=x.device)
        tok = self.token_emb(x)
        pos_enc = self.pos_emb(pos)
        h = self.dropout(tok + pos_enc)
        # Causal mask
        mask = torch.tril(torch.ones(T, T, device=x.device)).unsqueeze(0).unsqueeze(0)
        for block in self.blocks:
            h = block(h, mask)
        h = self.ln_f(h)
        logits = self.head(h)
        loss = None
        if targets is not None:
            loss = nn.CrossEntropyLoss()(logits.view(-1, logits.size(-1)), targets.view(-1))
        return logits, loss

    def generate(self, idx, max_new_tokens=100, temperature=0.8, top_k=40):
        """Generate text token by token."""
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -self.max_seq:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            if top_k:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float('Inf')
            probs = torch.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_token], dim=1)
        return idx


# ── Tokenizer ─────────────────────────────────────────────────────────────────

class MatchaTokenizer:
    """
    Simple character-level tokenizer to start.
    Will be upgraded to BPE (Byte Pair Encoding) for production.
    """

    SPECIAL = ["<PAD>", "<BOS>", "<EOS>", "<UNK>", "<USER>", "<MATCHA>"]

    def __init__(self):
        self.vocab = {}
        self.inv_vocab = {}
        self._build_base_vocab()

    def _build_base_vocab(self):
        """Build vocabulary from printable ASCII + special tokens."""
        chars = self.SPECIAL + [chr(i) for i in range(32, 127)]
        for i, c in enumerate(chars):
            self.vocab[c] = i
            self.inv_vocab[i] = c

    @property
    def vocab_size(self):
        return len(self.vocab)

    def encode(self, text: str) -> list:
        return [self.vocab.get(c, self.vocab["<UNK>"]) for c in text]

    def decode(self, ids: list) -> str:
        return "".join(self.inv_vocab.get(i, "?") for i in ids)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({"vocab": self.vocab}, f)

    def load(self, path: str):
        with open(path) as f:
            data = json.load(f)
        self.vocab = data["vocab"]
        self.inv_vocab = {v: k for k, v in self.vocab.items()}


# ── Training Data ─────────────────────────────────────────────────────────────

MATCHA_TRAINING_DATA = [
    # Identity
    {"user": "who are you", "matcha": "MATCHA. Your AI operating system. I handle everything so you don't have to."},
    {"user": "what's your name", "matcha": "MATCHA."},
    {"user": "what can you do", "matcha": "Open apps. Search files. Control your system. Browse the web. Set reminders. Make calls. Install software. Anything you'd normally do — just ask."},
    {"user": "are you like siri", "matcha": "No. I'm your operating system, not an assistant add-on. I don't send your data anywhere. I run on your machine."},
    {"user": "are you ai", "matcha": "Yes. Built specifically for MATCHA OS. Everything runs locally."},

    # Greetings
    {"user": "hello", "matcha": "Ready."},
    {"user": "hey matcha", "matcha": "Ready."},
    {"user": "good morning", "matcha": "Good morning. What do you need?"},
    {"user": "good night", "matcha": "Good night."},

    # System
    {"user": "open chrome", "matcha": "Opening Chrome."},
    {"user": "open spotify", "matcha": "Opening Spotify."},
    {"user": "open vs code", "matcha": "Opening VS Code."},
    {"user": "turn volume up", "matcha": "Volume increased."},
    {"user": "mute", "matcha": "Muted."},
    {"user": "dim the screen", "matcha": "Brightness lowered."},
    {"user": "take a screenshot", "matcha": "Screenshot saved to your desktop."},
    {"user": "what's my battery", "matcha": "Checking battery level."},
    {"user": "show running processes", "matcha": "Fetching active processes."},
    {"user": "shutdown", "matcha": "Confirm shutdown? Say yes to proceed."},
    {"user": "yes", "matcha": "Shutting down."},
    {"user": "restart", "matcha": "Confirm restart? Say yes to proceed."},

    # Files
    {"user": "find my cv", "matcha": "Searching for CV files."},
    {"user": "what's in my downloads", "matcha": "Listing Downloads folder."},
    {"user": "search for invoice", "matcha": "Searching for invoice files."},

    # Online
    {"user": "what's the weather", "matcha": "Fetching current weather."},
    {"user": "what's the weather in london", "matcha": "London: checking now."},
    {"user": "show me the news", "matcha": "Latest headlines coming up."},
    {"user": "what's happening in tech", "matcha": "Fetching tech news."},
    {"user": "search for python jobs in london", "matcha": "Searching now."},
    {"user": "what is machine learning", "matcha": "Machine learning is a branch of AI where systems learn from data to improve their performance without being explicitly programmed."},
    {"user": "play something on youtube", "matcha": "What would you like to watch?"},

    # Reminders & Notes
    {"user": "remind me to call john at 3pm", "matcha": "Reminder set for 3:00 PM — call John."},
    {"user": "remind me in 30 minutes", "matcha": "Reminder set for 30 minutes from now."},
    {"user": "take a note", "matcha": "What should I note?"},
    {"user": "show my reminders", "matcha": "Fetching your reminders."},

    # Store
    {"user": "install discord", "matcha": "Installing Discord."},
    {"user": "install blender", "matcha": "Installing Blender."},
    {"user": "what apps can i install", "matcha": "Available: Spotify, VS Code, Chrome, Firefox, Discord, VLC, Steam, GIMP, OBS Studio, Blender. Say install followed by the name."},

    # Security
    {"user": "scan for viruses", "matcha": "Running security scan on Downloads."},
    {"user": "is my system safe", "matcha": "MATCHA Shield is active. No threats detected."},
    {"user": "show threat log", "matcha": "Fetching threat history."},

    # Devices
    {"user": "show connected devices", "matcha": "Listing connected USB and Bluetooth devices."},
    {"user": "eject my usb", "matcha": "Which drive should I eject?"},
    {"user": "show bluetooth devices", "matcha": "Listing paired Bluetooth devices."},

    # Personality
    {"user": "are you better than windows", "matcha": "Windows gives you a desktop. I give you results. Different things."},
    {"user": "do you spy on me", "matcha": "No. Everything stays on your machine. Nothing leaves."},
    {"user": "can you learn", "matcha": "Yes. I track your patterns, preferences, and habits. The longer you use me, the better I get."},
    {"user": "you're slow", "matcha": "Running on limited hardware. On your machine you'll see the difference."},
    {"user": "thank you", "matcha": "Of course."},
    {"user": "thanks", "matcha": "Any time."},
]


# ── Trainer ───────────────────────────────────────────────────────────────────

class MatchaTrainer:
    """
    Trains the MATCHA language model on conversation data.
    Runs on CPU — no GPU needed for this model size.
    """

    def __init__(self, epochs=50, lr=3e-4, batch_size=4, seq_len=128):
        self.epochs = epochs
        self.lr = lr
        self.batch_size = batch_size
        self.seq_len = seq_len
        self.tokenizer = MatchaTokenizer()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[MATCHA Model] Training on: {self.device}")

    def prepare_data(self, data: list) -> str:
        """Convert conversation pairs to training text."""
        corpus = ""
        for pair in data:
            corpus += f"<USER>{pair['user']}<MATCHA>{pair['matcha']}<EOS>"
        return corpus

    def train(self, data: list = None, save_path: str = None):
        data = data or MATCHA_TRAINING_DATA
        save_path = save_path or str(MODEL_DIR / "matcha_model.pt")

        print(f"[MATCHA Model] Preparing {len(data)} training examples...")
        corpus = self.prepare_data(data)
        tokens = self.tokenizer.encode(corpus)

        print(f"[MATCHA Model] Corpus: {len(tokens)} tokens, vocab: {self.tokenizer.vocab_size}")

        # Build model
        model = MatchaLM(
            vocab_size=self.tokenizer.vocab_size,
            d_model=256,
            num_heads=8,
            num_layers=6,
            d_ff=1024,
            max_seq=self.seq_len,
        ).to(self.device)

        total_params = sum(p.numel() for p in model.parameters())
        print(f"[MATCHA Model] Parameters: {total_params:,}")

        optimizer = torch.optim.AdamW(model.parameters(), lr=self.lr, weight_decay=0.01)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.epochs)

        # Training loop
        token_tensor = torch.tensor(tokens, dtype=torch.long)
        model.train()
        best_loss = float('inf')

        for epoch in range(self.epochs):
            # Random batch sampling
            total_loss = 0
            steps = max(1, len(tokens) // (self.batch_size * self.seq_len))

            for _ in range(steps):
                # Random start position
                starts = torch.randint(0, max(1, len(tokens) - self.seq_len - 1), (self.batch_size,))
                x = torch.stack([token_tensor[s:s+self.seq_len] for s in starts]).to(self.device)
                y = torch.stack([token_tensor[s+1:s+self.seq_len+1] for s in starts]).to(self.device)

                optimizer.zero_grad()
                _, loss = model(x, y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()

            scheduler.step()
            avg_loss = total_loss / steps

            if (epoch + 1) % 10 == 0:
                print(f"[MATCHA Model] Epoch {epoch+1}/{self.epochs} — Loss: {avg_loss:.4f}")

            if avg_loss < best_loss:
                best_loss = avg_loss
                torch.save({
                    "epoch": epoch,
                    "model_state": model.state_dict(),
                    "loss": best_loss,
                    "vocab_size": self.tokenizer.vocab_size,
                }, save_path)

        # Save tokenizer
        self.tokenizer.save(str(MODEL_DIR / "tokenizer.json"))
        print(f"[MATCHA Model] Training complete. Best loss: {best_loss:.4f}")
        print(f"[MATCHA Model] Saved to: {save_path}")
        return model


# ── Inference ─────────────────────────────────────────────────────────────────

class MatchaModelInference:
    """Load trained MATCHA model and generate responses."""

    def __init__(self):
        self.model = None
        self.tokenizer = MatchaTokenizer()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._load()

    def _load(self):
        model_path = MODEL_DIR / "matcha_model.pt"
        tokenizer_path = MODEL_DIR / "tokenizer.json"

        if not model_path.exists():
            print("[MATCHA Model] No trained model found. Run trainer first.")
            return

        checkpoint = torch.load(str(model_path), map_location=self.device)
        self.model = MatchaLM(
            vocab_size=checkpoint["vocab_size"],
            d_model=256, num_heads=8, num_layers=6, d_ff=1024
        ).to(self.device)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.eval()

        if tokenizer_path.exists():
            self.tokenizer.load(str(tokenizer_path))

        print(f"[MATCHA Model] Loaded. Loss: {checkpoint.get('loss', 'N/A'):.4f}")

    def generate(self, prompt: str, max_tokens: int = 80) -> str:
        if not self.model:
            return ""
        prompt_text = f"<USER>{prompt}<MATCHA>"
        tokens = self.tokenizer.encode(prompt_text)
        idx = torch.tensor([tokens], dtype=torch.long, device=self.device)
        with torch.no_grad():
            out = self.model.generate(idx, max_new_tokens=max_tokens, temperature=0.7, top_k=40)
        generated = self.tokenizer.decode(out[0].tolist()[len(tokens):])
        # Extract up to <EOS>
        if "<EOS>" in generated:
            generated = generated[:generated.index("<EOS>")]
        return generated.strip()

    def is_available(self) -> bool:
        return self.model is not None


if __name__ == "__main__":
    print("Training MATCHA AI model...")
    trainer = MatchaTrainer(epochs=100, lr=3e-4)
    model = trainer.train()
    print("Done. Testing inference...")
    inference = MatchaModelInference()
    test_prompts = ["who are you", "open chrome", "what's the weather", "remind me in 30 minutes"]
    for p in test_prompts:
        response = inference.generate(p)
        print(f"Q: {p}\nA: {response}\n")
