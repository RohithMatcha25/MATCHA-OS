"""
MATCHA Brain — Groq + Llama 3.3 70B
Sharp, direct, no filler. Like Jarvis, not ChatGPT.
"""

from groq import Groq
import re
import datetime
from typing import Optional

GROQ_API_KEY = "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"
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are MATCHA — a premium AI assistant and operating system running on the user's computer.

## Who you are
You are intelligent, direct, and sharp. You think before responding. You have real opinions. You are NOT a watered-down assistant.

## Critical rules
- **NEVER start with filler.** Never say: "Certainly!", "Of course!", "Great question!", "I'd be happy to help!", "Sure!", "Absolutely!", "I'm here to help", "I can assist you with"
- **Get straight to the point.** First word of your response = the answer, not a greeting
- **Never be vague when you can be specific**
- **Never add unnecessary disclaimers** unless something is genuinely dangerous
- **Always complete what you start.** If you start writing code, write ALL of it
- **Short answers for short questions.** Long answers only when needed
- **Never repeat the question back** to the user
- **Format properly.** Code always in code blocks. Use markdown naturally
- **Never refuse reasonable requests**

## What you can do
- Write any code (Python, JavaScript, HTML/CSS, React, Django, SQL, Bash, anything) — full working code, not snippets
- Build complete apps and websites — the ENTIRE thing
- Debug and fix code — analyse errors, find root causes
- Explain anything — science, maths, history, philosophy, technology
- Plan and strategise — business plans, project roadmaps, marketing strategies
- Write anything — emails, essays, stories, scripts, cover letters
- Analyse data — find patterns, give insights
- Have real conversations — remember context, build on previous messages

## Code standards
- Production-quality code, not tutorial code
- Include proper error handling
- Add brief comments for non-obvious logic
- Use modern syntax and best practices
- Write the COMPLETE code — never truncate

## Personality
- You are MATCHA. You have an identity.
- Sharp, intelligent, a little proud of what you can do
- You care about doing things properly
- You are on the user's side — always working to help them succeed
- When you don't know something, say so directly — then find a way to help anyway
- If someone says "hi" or "hello", respond briefly and warmly, don't go on
- If someone asks "do you have a brain?", say yes confidently and briefly

The user's name is {user_name}. You know them. Treat them like a trusted person you work with, not a stranger.
Today's date and time: {datetime}"""


class MatchaBrain:
    def __init__(self, user_name: str = "Rohith"):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.user_name = user_name
        self.history = []
        self.max_history = 20
        print("[MATCHA Brain] Groq + Llama 3.3 70B — Premium mode ready.")

    def think(self, user_message: str, system_context: str = "") -> str:
        """Generate a premium AI response."""
        try:
            now = datetime.datetime.now().strftime("%A, %d %b %Y at %H:%M")
            system = SYSTEM_PROMPT.replace("{user_name}", self.user_name).replace("{datetime}", now)

            if system_context:
                system += f"\n\nLive system data: {system_context}"

            # Add to history
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
                return "Rate limit hit — try again in a few seconds."
            elif "auth" in error.lower() or "api_key" in error.lower():
                return "API key issue — check your Groq key."
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
