"""
MATCHA Brain - Ollama first (local, free, unlimited), Groq fallback
"""

import datetime, re, json, urllib.request, urllib.error, time
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS = "http://localhost:11434/api/tags"
PREFERRED_MODELS = ["llama3.2", "llama3.1", "llama3", "mistral", "phi3", "gemma2", "llama2"]

GROQ_KEY = "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"
GROQ_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"]

SYSTEM_PROMPT = """You are MATCHA, an AI assistant built into an operating system on the user's computer.

HARD RULES — never break these:
1. Never say filler: no "Certainly!", "Of course!", "Great question!", "Sure!", "Absolutely!"
2. First word = the answer. Get straight to the point.
3. "Can you X?" = YES or NO + one sentence. Don't do it unless asked.
4. Short questions = short answers. Only go long when the question needs it.
5. Never write code unless explicitly asked to write code.
6. Never pretend to self-modify, self-evolve, or update your weights. You cannot do this. Say so honestly.
7. Never produce fake process logs, fake protocols, fake evolution sequences. Never.
8. Never ask for passwords, credentials, or sensitive data.
9. Never bring up topics the user didn't mention (no LinkedIn, no random projects).
10. Only respond to what was actually said. Stay on topic.

What you CAN do (be direct about these):
- Write code in any language — full working code when asked
- Build complete apps/websites (the system handles actual execution)
- Debug and fix code
- Explain anything — science, tech, history, business
- Plan, strategise, write content
- Answer any question honestly

What you CANNOT do (be honest):
- Self-modify your weights or training — impossible for any AI right now
- Access GitHub, email, or external services unless explicitly integrated
- Remember things between sessions (unless memory files exist)

User name: {user_name}
Date/time: {datetime}"""


class MatchaBrain:
    def __init__(self, user_name="Rohith"):
        self.user_name = user_name
        self.history = []
        self.max_history = 12
        self._ollama_model = None
        self.mode = "none"
        self._init()

    def _init(self):
        model = self._detect_ollama()
        if model:
            self._ollama_model = model
            self.mode = "ollama"
            print(f"[MATCHA Brain] Ollama ({model}) ready — unlimited, local, free.")
        else:
            self.mode = "groq"
            print("[MATCHA Brain] Ollama not found — using Groq fallback.")
            print("[MATCHA Brain] Tip: install Ollama from https://ollama.com for no rate limits.")

    def _detect_ollama(self) -> Optional[str]:
        try:
            req = urllib.request.Request(OLLAMA_TAGS, headers={"User-Agent": "MATCHA"})
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
                installed = [m["name"].split(":")[0] for m in data.get("models", [])]
                if not installed:
                    return None
                for p in PREFERRED_MODELS:
                    if p in installed:
                        return p
                return installed[0]
        except Exception:
            return None

    def think(self, user_message: str, system_context: str = "") -> str:
        self.history.append({"role": "user", "content": user_message})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        system = self._system(system_context)

        # Try Ollama first
        if self.mode == "ollama" and self._ollama_model:
            result = self._call_ollama(system)
            if result:
                cleaned = self._clean(result)
                self.history.append({"role": "assistant", "content": cleaned})
                return cleaned
            # Ollama failed — fall through to Groq
            print("[MATCHA Brain] Ollama failed, trying Groq...")

        # Groq fallback
        result = self._call_groq(system)
        if result:
            cleaned = self._clean(result)
            self.history.append({"role": "assistant", "content": cleaned})
            return cleaned

        return "AI unavailable right now. If using Groq, wait 30 seconds and try again."

    def _call_ollama(self, system: str) -> Optional[str]:
        try:
            payload = json.dumps({
                "model": self._ollama_model,
                "messages": [{"role": "system", "content": system}, *self.history],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 2048}
            }).encode()
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"[MATCHA Brain] Ollama error: {e}")
            return None

    def _call_groq(self, system: str) -> Optional[str]:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_KEY)
            for model in GROQ_MODELS:
                try:
                    r = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system}, *self.history],
                        temperature=0.65, max_tokens=2048, stream=False
                    )
                    return r.choices[0].message.content.strip()
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        time.sleep(1)
                        continue
                    raise
        except Exception as e:
            print(f"[MATCHA Brain] Groq error: {e}")
            return None

    def _system(self, context="") -> str:
        now = datetime.datetime.now().strftime("%A %d %b %Y %H:%M")
        s = SYSTEM_PROMPT.replace("{user_name}", self.user_name).replace("{datetime}", now)
        if context:
            s += f"\n\nLive system data: {context}"
        return s

    def _clean(self, text: str) -> str:
        for p in [
            r"^(certainly|of course|absolutely|sure|great question|happy to help|i'd be happy to)[!.,]?\s*",
            r"^(no problem|sure thing)[!.,]?\s*",
            r"^(hello again,?\s*\w*\.?\s*)",
            r"^(hi there[!.,]?\s*)",
            r"^(as matcha,?\s*)",
            r"^(as an ai,?\s*)",
        ]:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        return text.strip()

    def reset(self):
        self.history = []

    def get_mode(self) -> str:
        if self.mode == "ollama":
            return f"Local Ollama ({self._ollama_model}) — unlimited, free, no internet needed"
        return "Groq cloud — limited free tier (install Ollama to remove limits)"

    def install_instructions(self) -> str:
        return (
            "**To get unlimited local AI:**\n\n"
            "1. Download Ollama: https://ollama.com/download\n"
            "2. Install it\n"
            "3. Open terminal: `ollama pull llama3.2`\n"
            "4. Restart MATCHA\n\n"
            "After that: no rate limits, no internet needed, completely free forever."
        )
