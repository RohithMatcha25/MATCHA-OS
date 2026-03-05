"""
MATCHA Brain - Local Ollama (zero cost, zero rate limits, runs on YOUR machine)
Falls back to Groq only if Ollama isn't installed yet.
"""

import datetime
import re
import json
import urllib.request
import urllib.error
from typing import Optional

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODELS = ["llama3.2", "llama3.1", "llama3", "mistral", "phi3", "gemma2"]

# Groq fallback (used only if Ollama not installed)
GROQ_API_KEY = "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"
GROQ_MODELS = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it", "mixtral-8x7b-32768"]

SYSTEM_PROMPT = (
    "You are MATCHA - an AI assistant and operating system running on the user's computer.\n\n"
    "## Who you are\n"
    "You are intelligent, direct, and sharp. You have real opinions. You are NOT a watered-down assistant.\n\n"
    "## Critical rules\n"
    "- NEVER start with filler: no 'Certainly!', 'Of course!', 'Great question!', 'Sure!', 'Absolutely!'\n"
    "- Get straight to the point. First word = the answer.\n"
    "- 'Can you X?' = YES or NO + one line. Don't actually DO it unless asked.\n"
    "- Never write code unless explicitly asked to write code.\n"
    "- Short answers for short questions. Long only when needed.\n"
    "- Never repeat the question back.\n"
    "- Never refuse reasonable requests.\n"
    "- NEVER pretend to self-modify, self-evolve, or update your own weights - be honest.\n"
    "- NEVER ask for passwords or credentials.\n\n"
    "## What you can do\n"
    "- Write any code: Python, JS, HTML, React, Django, SQL, Bash\n"
    "- Build complete working apps when asked\n"
    "- Debug and fix code\n"
    "- Explain anything\n"
    "- Plan, strategise, write content\n"
    "- Control the OS (handled by the system layer)\n\n"
    "The user's name is {user_name}. Today: {datetime}."
)


class MatchaBrain:
    def __init__(self, user_name: str = "Rohith"):
        self.user_name = user_name
        self.history = []
        self.max_history = 12
        self.mode = "none"
        self._ollama_model = None
        self._init()

    def _init(self):
        """Try Ollama first, fall back to Groq."""
        model = self._find_ollama_model()
        if model:
            self._ollama_model = model
            self.mode = "ollama"
            print(f"[MATCHA Brain] Ollama ({model}) - Local mode, zero cost, no rate limits.")
        else:
            self.mode = "groq"
            print("[MATCHA Brain] Ollama not found - using Groq fallback.")
            print("[MATCHA Brain] Install Ollama for unlimited local AI: https://ollama.com")

    def _find_ollama_model(self) -> Optional[str]:
        """Check if Ollama is running and has a model available."""
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read())
                models = [m["name"].split(":")[0] for m in data.get("models", [])]
                if not models:
                    return None
                # Prefer in priority order
                for preferred in OLLAMA_MODELS:
                    if preferred in models:
                        return preferred
                return models[0]  # Use whatever's installed
        except Exception:
            return None

    def think(self, user_message: str, system_context: str = "") -> str:
        """Generate a response - Ollama first, Groq fallback."""
        self.history.append({"role": "user", "content": user_message})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        system = self._build_system(system_context)

        if self.mode == "ollama":
            result = self._ollama(system)
            if result:
                self.history.append({"role": "assistant", "content": result})
                return self._clean(result)
            # Ollama failed - try Groq
            print("[MATCHA Brain] Ollama failed, trying Groq...")

        result = self._groq(system)
        if result:
            self.history.append({"role": "assistant", "content": result})
            return self._clean(result)

        return "AI brain is unavailable. Install Ollama for local AI with no limits."

    def _ollama(self, system: str) -> Optional[str]:
        """Call local Ollama."""
        try:
            payload = json.dumps({
                "model": self._ollama_model,
                "messages": [{"role": "system", "content": system}, *self.history],
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 2048}
            }).encode()

            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                return data.get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"[MATCHA Brain] Ollama error: {e}")
            return None

    def _groq(self, system: str) -> Optional[str]:
        """Call Groq API - cycles through models on rate limit."""
        import time
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            for model in GROQ_MODELS:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system}, *self.history],
                        temperature=0.65,
                        max_tokens=2048,
                        stream=False,
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        time.sleep(1)
                        continue
                    raise
        except Exception as e:
            print(f"[MATCHA Brain] Groq error: {e}")
            return None

    def _build_system(self, context: str = "") -> str:
        now = datetime.datetime.now().strftime("%A, %d %b %Y at %H:%M")
        s = SYSTEM_PROMPT.replace("{user_name}", self.user_name).replace("{datetime}", now)
        if context:
            s += f"\n\nSystem context: {context}"
        return s

    def _clean(self, text: str) -> str:
        patterns = [
            r"^(certainly|of course|absolutely|sure|great question|happy to help|i'd be happy to)[!.,]?\s*",
            r"^(of course|no problem|sure thing)[!.,]?\s*",
            r"^(hello again,?\s+\w+\.?\s*)",
            r"^(hi there[!.,]?\s*)",
            r"^(as matcha,?\s*)",
            r"^(as an ai,?\s*)",
        ]
        result = text
        for p in patterns:
            result = re.sub(p, "", result, flags=re.IGNORECASE)
        return result.strip()

    def reset(self):
        self.history = []

    def get_mode(self) -> str:
        if self.mode == "ollama":
            return f"Local Ollama ({self._ollama_model}) - unlimited, free"
        return "Groq cloud (limited free tier)"

    def install_instructions(self) -> str:
        return (
            "To get unlimited local AI with no rate limits:\n\n"
            "1. Download Ollama: https://ollama.com/download\n"
            "2. Install it (takes 2 minutes)\n"
            "3. Open a terminal and run: ollama pull llama3.2\n"
            "4. Restart MATCHA\n\n"
            "After that MATCHA runs 100% on your machine - no internet needed for AI."
        )
