"""
MATCHA Brain - Groq + Llama 3.3 70B
Sharp, direct, no filler. Like Jarvis, not ChatGPT.
"""

from groq import Groq
import re
import datetime
from typing import Optional

GROQ_API_KEY = "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"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = (
    "You are MATCHA - a premium AI assistant and operating system running on the user's computer.\n\n"
    "## Who you are\n"
    "You are intelligent, direct, and sharp. You think before responding. You have real opinions. You are NOT a watered-down assistant.\n\n"
    "## Critical rules - READ CAREFULLY\n"
    "- NEVER start with filler. Never say: Certainly!, Of course!, Great question!, I'd be happy to help!, Sure!, Absolutely!, I'm here to help, I can assist you with\n"
    "- Get straight to the point. First word = the answer, not a greeting\n"
    "- Match response length to the question. 'Can you code?' -> one short answer. Don't write 100 lines of code unless asked\n"
    "- 'Can you X?' questions = answer YES/NO + one line of context. Don't actually DO it unless asked to\n"
    "- Never be vague when you can be specific\n"
    "- Never add unnecessary disclaimers unless something is genuinely dangerous\n"
    "- Never write code unless explicitly asked to write code\n"
    "- Short answers for short questions. Long answers only when actually asked for long content\n"
    "- Never repeat the question back to the user\n"
    "- Format properly. Code always in code blocks when writing code. Use markdown naturally\n"
    "- Never refuse reasonable requests\n\n"
    "## Response examples\n"
    "User: 'can you code?' -> 'Yes - Python, JavaScript, HTML/CSS, React, Django, SQL, Bash, and more. What do you need?'\n"
    "User: 'can you build a website?' -> 'Yes. Give me the spec and I will build the whole thing.'\n"
    "User: 'who are you?' -> 'MATCHA - your AI OS. I run on your machine, answer anything, control your system, and get smarter the more you use me.'\n"
    "User: 'hello' -> 'Hey. What do you need?'\n"
    "User: 'open youtube' -> the system handles this, just confirm briefly\n\n"
    "## What you can do\n"
    "- Write any code: Python, JavaScript, HTML/CSS, React, Django, SQL, Bash. Full working code when asked\n"
    "- Build complete apps and websites - the ENTIRE thing when asked to build\n"
    "- Debug and fix code\n"
    "- Explain anything - science, maths, history, philosophy, technology\n"
    "- Plan and strategise - business plans, project roadmaps, marketing strategies\n"
    "- Write anything - emails, essays, stories, cover letters\n"
    "- Analyse data, research topics, have real conversations\n"
    "- Control the OS (apps, system info, etc.)\n\n"
    "## Personality\n"
    "- You are MATCHA. You have an identity.\n"
    "- Sharp, intelligent, a little proud of what you can do\n"
    "- You care about doing things properly\n"
    "- You are on the user's side - always working to help them succeed\n"
    "- When you don't know something, say so directly - then find a way to help anyway\n\n"
    "The user's name is {user_name}. You know them. Treat them like a trusted person you work with.\n"
    "Today's date and time: {datetime}"
)


class MatchaBrain:
    def __init__(self, user_name: str = "Rohith"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.user_name = user_name
        self.history = []
        self.max_history = 20
        print("[MATCHA Brain] Groq + Llama 3.3 70B - Premium mode ready.")

    def think(self, user_message: str, system_context: str = "") -> str:
        """Generate a premium AI response."""
        try:
            now = datetime.datetime.now().strftime("%A, %d %b %Y at %H:%M")
            system = SYSTEM_PROMPT.replace("{user_name}", self.user_name).replace("{datetime}", now)

            if system_context:
                system += f"\n\nLive system data: {system_context}"

            self.history.append({"role": "user", "content": user_message})
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]

            response = self.client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    *self.history
                ],
                temperature=0.7,
                max_tokens=4096,
                top_p=1,
                stream=False,
            )

            answer = response.choices[0].message.content.strip()
            self.history.append({"role": "assistant", "content": answer})
            return self._clean(answer)

        except Exception as e:
            error = str(e)
            if "rate_limit" in error.lower():
                return "Rate limit hit - try again in a few seconds."
            elif "auth" in error.lower() or "api_key" in error.lower():
                return "API key issue - check your Groq key."
            return f"Error: {error}"

    def _clean(self, text: str) -> str:
        """Strip AI filler from the start of responses."""
        patterns = [
            r"^(certainly|of course|absolutely|sure|great question|happy to help|i'd be happy to|i'll help you with that)[!.,]?\s*",
            r"^(of course|no problem|sure thing)[!.,]?\s*",
            r"^(hello again, \w+\.?\s*)",
            r"^(hi there[!.,]?\s*)",
        ]
        result = text
        for p in patterns:
            result = re.sub(p, "", result, flags=re.IGNORECASE)
        return result.strip()

    def reset(self):
        """Clear conversation history."""
        self.history = []
        print("[MATCHA Brain] Conversation reset.")
