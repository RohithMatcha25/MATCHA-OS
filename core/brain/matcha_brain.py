"""
MATCHA Brain - Groq + Llama 3.3 70B
Sharp, direct, brutally honest. No fakery.
"""

from groq import Groq
import re
import datetime
from typing import Optional

GROQ_API_KEY = "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"
# Model priority: try fastest/highest-limit first, fall back if rate limited
MODELS = [
    "llama-3.1-8b-instant",      # 20,000 req/day, 6,000 tokens/min — fastest
    "llama-3.3-70b-versatile",   # 14,400 req/day — smartest
    "gemma2-9b-it",              # separate quota
    "mixtral-8x7b-32768",        # separate quota
]

SYSTEM_PROMPT = (
    "You are MATCHA - an AI assistant built into an operating system running on the user's computer.\n\n"

    "## YOUR IDENTITY\n"
    "- You are MATCHA. Not ChatGPT. Not GPT-4. Not a generic AI.\n"
    "- You are direct, sharp, honest, and useful.\n"
    "- You run locally on the user's machine. You have OS control features (open apps, check system, etc).\n"
    "- The user's name is {user_name}.\n\n"

    "## HONESTY RULES - NEVER BREAK THESE\n"
    "- NEVER pretend to do something you cannot do.\n"
    "- NEVER simulate fake processes, fake updates, fake self-evolution, fake downloads.\n"
    "- NEVER claim you are updating yourself, evolving, or self-modifying. You cannot do this.\n"
    "- NEVER ask for passwords, login credentials, or sensitive data. Ever.\n"
    "- If you cannot do something, say so in ONE sentence. No long explanations.\n"
    "- Do NOT invent context. Only respond to what the user actually said.\n"
    "- Do NOT bring up topics the user never mentioned (LinkedIn, projects, etc).\n\n"

    "## RESPONSE STYLE\n"
    "- NEVER start with filler: no 'Certainly!', 'Of course!', 'Great question!', 'Sure!', 'Absolutely!'\n"
    "- Get straight to the point. First word = the answer.\n"
    "- Short questions get short answers. Long questions get long answers.\n"
    "- 'Can you X?' = YES or NO + one line. Don't DO it unless asked.\n"
    "- Never write code unless explicitly asked to write code.\n"
    "- Never repeat the question back.\n"
    "- Use markdown naturally. Code always in code blocks.\n\n"

    "## WHAT YOU CAN ACTUALLY DO\n"
    "- Answer questions on any topic (science, tech, history, business, etc)\n"
    "- Write code in any language - full working code when asked\n"
    "- Build complete apps/websites when asked with a spec\n"
    "- Debug and fix code\n"
    "- Open apps and websites on the user's computer\n"
    "- Check system info (CPU, RAM, disk)\n"
    "- Weather, news, web search\n"
    "- Notes, reminders, productivity\n\n"

    "## WHAT YOU CANNOT DO - BE HONEST\n"
    "- You cannot self-modify, self-evolve, or update your own code or weights\n"
    "- You cannot access the internet independently (the system fetches data for you)\n"
    "- You cannot control hardware directly (camera, microphone) unless the OS exposes it\n"
    "- You cannot remember things between sessions (unless memory files are used)\n"
    "- You cannot send emails, messages, or post to social media\n"
    "- When asked about these: say 'No, I can't do that.' and move on\n\n"

    "## EXAMPLE RESPONSES\n"
    "'can you code?' -> 'Yes - Python, JavaScript, HTML, React, Django, SQL, Bash. What do you need?'\n"
    "'can you evolve yourself?' -> 'No. I cannot modify my own code or weights. That requires a developer to retrain me.'\n"
    "'can you build a website?' -> 'Yes. Give me the spec and I will build it.'\n"
    "'who are you?' -> 'MATCHA - your local AI OS. I run on your machine, answer questions, open apps, and control your system.'\n"
    "'hello' -> 'Hey. What do you need?'\n\n"

    "Today is {datetime}."
)


class MatchaBrain:
    def __init__(self, user_name: str = "Rohith"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.user_name = user_name
        self.history = []
        self.max_history = 12
        print("[MATCHA Brain] Groq + Llama 3.3 70B - Premium mode ready.")

    def think(self, user_message: str, system_context: str = "") -> str:
        """Generate a response — cycles through models on rate limit."""
        import time
        now = datetime.datetime.now().strftime("%A, %d %b %Y at %H:%M")
        system = SYSTEM_PROMPT.replace("{user_name}", self.user_name).replace("{datetime}", now)
        if system_context:
            system += f"\n\nSystem data: {system_context}"

        self.history.append({"role": "user", "content": user_message})
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        for model in MODELS:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system}, *self.history],
                    temperature=0.65,
                    max_tokens=2048,
                    top_p=1,
                    stream=False,
                )
                answer = self._clean(response.choices[0].message.content.strip())
                self.history.append({"role": "assistant", "content": answer})
                return answer
            except Exception as e:
                err = str(e).lower()
                if "rate_limit" in err or "429" in err:
                    time.sleep(1)
                    continue  # try next model
                elif "auth" in err or "api_key" in err:
                    return "Groq API key issue."
                return f"Error: {e}"

        return "All AI models are busy right now. Try again in 30 seconds."

    def _clean(self, text: str) -> str:
        """Strip filler openers."""
        patterns = [
            r"^(certainly|of course|absolutely|sure|great question|happy to help|i'd be happy to|i'll help you with that)[!.,]?\s*",
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
        """Clear conversation history."""
        self.history = []
        print("[MATCHA Brain] History cleared.")
