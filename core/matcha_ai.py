"""
MATCHA AI — Core Brain v4.0
- Self-learning: learns facts from web when online, stores locally
- Permission system: asks before doing anything that affects your system
- Smart intent routing: "open youtube" opens browser
- Groq brain handles all general queries
"""

import json
import os
import re
import datetime
import sqlite3
from pathlib import Path
from collections import deque

MEMORY_DB = Path(__file__).parent / "memory" / "matcha_memory.db"
MATCHA_VERSION = "0.4.0"

# ── Known apps that should open in browser (not installed as desktop apps) ──
BROWSER_APPS = {
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://www.google.com",
    "facebook": "https://www.facebook.com",
    "twitter": "https://www.twitter.com",
    "instagram": "https://www.instagram.com",
    "netflix": "https://www.netflix.com",
    "reddit": "https://www.reddit.com",
    "github": "https://www.github.com",
    "linkedin": "https://www.linkedin.com",
    "amazon": "https://www.amazon.co.uk",
    "whatsapp": "https://web.whatsapp.com",
    "spotify": "https://open.spotify.com",
    "maps": "https://maps.google.com",
    "translate": "https://translate.google.com",
    "drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "calendar": "https://calendar.google.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "bard": "https://bard.google.com",
    "outlook": "https://outlook.live.com",
    "onedrive": "https://onedrive.live.com",
    "dropbox": "https://www.dropbox.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "bbc": "https://www.bbc.co.uk",
    "ebay": "https://www.ebay.co.uk",
}

# ── Desktop apps (installed locally) ──
DESKTOP_APPS = {
    "chrome": ["chrome", "google-chrome", "chromium"],
    "firefox": ["firefox"],
    "edge": ["msedge", "microsoft-edge"],
    "brave": ["brave-browser", "brave"],
    "terminal": ["cmd", "powershell", "gnome-terminal", "xterm"],
    "notepad": ["notepad"],
    "calculator": ["calc", "gnome-calculator"],
    "explorer": ["explorer"],
    "vscode": ["code"],
    "vs code": ["code"],
    "visual studio code": ["code"],
    "word": ["winword"],
    "excel": ["excel"],
    "powerpoint": ["powerpnt"],
    "paint": ["mspaint"],
    "task manager": ["taskmgr"],
    "control panel": ["control"],
    "settings": ["ms-settings:"],
    "vlc": ["vlc"],
    "steam": ["steam"],
    "discord": ["discord"],
    "slack": ["slack"],
    "zoom": ["zoom"],
    "teams": ["teams"],
}


class MatchaAI:
    def __init__(self):
        self.online = False
        self.user_name = "User"
        self.memory = MatchaMemory(MEMORY_DB)
        self.personality = MatchaPersonality()
        self._conversation_context = deque(maxlen=10)
        self._web_agent = None
        self._system_control = None
        self._device_manager = None
        self._shield = None
        self._retriever = None
        self._load_retriever()
        self._thinker = None
        self._brain = None
        self._learner = None
        self._perms = None
        self._init_brain()
        self._init_learner()
        self._init_perms()
        print(f"[MATCHA] Core AI initialised — v{MATCHA_VERSION}")

    def _init_brain(self):
        """Load the Groq-powered brain."""
        try:
            from core.brain.matcha_brain import MatchaBrain
            self._brain = MatchaBrain(self.user_name)
        except Exception as e:
            print(f"[MATCHA] Brain unavailable: {e}")
            self._brain = None

    def _init_learner(self):
        """Load the self-learning engine."""
        try:
            from core.learning.self_learner import SelfLearner
            self._learner = SelfLearner()
        except Exception as e:
            print(f"[MATCHA] Learner unavailable: {e}")
            self._learner = None

    def _init_perms(self):
        """Load the permission manager."""
        try:
            from core.permissions.permission_manager import PermissionManager
            self._perms = PermissionManager()
        except Exception as e:
            print(f"[MATCHA] Permissions unavailable: {e}")
            self._perms = None

    def _load_retriever(self):
        """Load trained MATCHA model for fallback reasoning."""
        try:
            import json as _json, math as _math
            model_path = Path(__file__).parent / "model" / "weights" / "matcha_model.json"
            if not model_path.exists():
                return
            with open(model_path) as f:
                data = _json.load(f)
            index = []
            for inp, out in data["pairs"]:
                words = set(inp.lower().split())
                t = inp.lower()
                ng = set(t[i:i+2] for i in range(len(t)-1)) | set(t[i:i+3] for i in range(len(t)-2))
                index.append({"input": inp, "output": out, "words": words, "ngrams": ng})
            self._retriever = index
            print(f"[MATCHA] Model loaded: {len(index)} examples.")
        except Exception as e:
            print(f"[MATCHA] Model load failed: {e}")

    def _retriever_predict(self, query: str):
        if not self._retriever:
            return None
        import math
        q = query.lower().strip()
        q_words = set(q.split())
        q_ng = set(q[i:i+2] for i in range(len(q)-1)) | set(q[i:i+3] for i in range(len(q)-2))
        best_score, best_response = -1, ""
        for item in self._retriever:
            denom = math.sqrt(max(len(q_words),1)) * math.sqrt(max(len(item["words"]),1))
            word_s = len(q_words & item["words"]) / max(denom, 1)
            ng_s = len(q_ng & item["ngrams"]) / max(len(q_ng | item["ngrams"]), 1)
            score = word_s * 0.6 + ng_s * 0.4
            if score > best_score:
                best_score = score
                best_response = item["output"]
        return best_response if best_score >= 0.65 else None

    def set_online(self, status: bool):
        self.online = status
        mode = "Connected" if status else "Local Mode"
        if status and self._web_agent is None:
            self._load_web_agent()
        print(f"[MATCHA] Mode: {mode}")

    def _load_web_agent(self):
        try:
            from core.online.web_agent import WebAgent
            self._web_agent = WebAgent()
        except Exception as e:
            print(f"[MATCHA] Web agent load failed: {e}")

    def _load_system_control(self):
        try:
            from core.system.system_control import SystemControl
            self._system_control = SystemControl()
        except Exception as e:
            print(f"[MATCHA] System control load failed: {e}")

    def _load_device_manager(self):
        try:
            from core.devices.device_manager import DeviceManager
            self._device_manager = DeviceManager(
                on_device_connected=self._on_device_event,
                on_device_disconnected=self._on_device_event
            )
        except Exception as e:
            print(f"[MATCHA] Device manager load failed: {e}")

    def _load_shield(self):
        try:
            from core.security.matcha_shield import MatchaShield
            self._shield = MatchaShield(alert_callback=self._on_threat)
        except Exception as e:
            print(f"[MATCHA] Shield load failed: {e}")

    def _on_device_event(self, device: dict):
        action = device.get("action", "connected")
        name = device.get("name", "Unknown device")
        print(f"[MATCHA] Device {action}: {name}")

    def _on_threat(self, threat: dict):
        print(f"[MATCHA Shield] THREAT: {threat['file']} — {threat['threat']}")

    def think(self, user_input: str) -> str:
        """
        Main reasoning loop.
        Takes user input → reasons about intent → returns response.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        # ── Check if this is a yes/no to a pending permission ──
        if self._perms:
            is_confirm, is_yes, always = self._perms.is_confirmation(user_input)
            if is_confirm:
                pending = self._perms.get_pending()
                if pending:
                    if is_yes:
                        result = self._perms.confirm(pending["token"], always=always)
                        if result.get("proceed"):
                            return self._execute_permitted_action(result)
                    else:
                        self._perms.deny(pending.get("token", ""))
                        return "Got it. Action cancelled."

        # Detect intent
        intent = self._detect_intent(user_input)

        # Log to memory with intent
        self.memory.log_interaction(user_input, intent)

        # Track interest for self-learner
        if self._learner and self.online and intent in ("general", "identity"):
            # Learn in background — don't block response
            pass

        # Update conversation context
        self._conversation_context.append({"role": "user", "text": user_input, "intent": intent})

        # Route to handler
        response = self._handle_intent(intent, user_input)

        # Apply MATCHA personality
        response = self.personality.format(response, intent)

        # If response is an OPEN_URL command (no permission needed for info commands)
        # or a permission request — return as-is
        if response.startswith("__OPEN_URL__") or response.startswith("__ASK_PERMISSION__"):
            return response

        # Log response
        self._conversation_context.append({"role": "matcha", "text": response})

        # Self-learn: if we answered a factual query, remember it
        if self._learner and self.online and intent == "general":
            try:
                self._learner.learn_and_store(
                    topic=self._learner._extract_topic(user_input),
                    fact=response[:500],
                    source="groq_brain"
                )
            except Exception:
                pass

        return response

    def _execute_permitted_action(self, result: dict) -> str:
        """Execute an action after user gave permission."""
        action_type = result.get("action_type")
        data = result.get("action_data", {})
        always = data.get("always", False)

        suffix = " I'll always do this without asking next time." if always else ""

        if action_type == "open_browser":
            url = data.get("url", "")
            label = data.get("label", url)
            return f"__OPEN_URL__{url}__LABEL__{label}"

        elif action_type == "open_app":
            app = data.get("app", "")
            sc = self._get_system_control()
            if sc:
                res = sc.launch_app(app)
                return res.get("summary", f"Launched {app}.") + suffix
            return f"Launching {app}." + suffix

        elif action_type == "install_app":
            app = data.get("app", "")
            store = self._get_store()
            if store:
                return store.install(app) + suffix
            return f"Installing {app}." + suffix

        elif action_type == "shutdown":
            sc = self._get_system_control()
            if sc:
                return sc.shutdown().get("summary", "Shutting down.")

        elif action_type == "restart":
            sc = self._get_system_control()
            if sc:
                return sc.restart().get("summary", "Restarting.")

        elif action_type == "kill_process":
            sc = self._get_system_control()
            if sc:
                return sc.kill_process(data.get("process", "")).get("summary", "Process terminated.")

        return "Done."

    def _detect_intent(self, text: str) -> str:
        """Detect the intent of user input."""
        t = text.lower().strip()

        # ── System control (must come before 'open') ──
        if any(w in t for w in ["volume up", "volume down", "increase volume", "decrease volume",
                                  "turn up", "turn down", "louder", "quieter"]):
            return "system_control"
        if any(w in t for w in ["mute", "unmute"]):
            return "system_control"
        if any(w in t for w in ["brightness up", "brightness down", "increase brightness", "decrease brightness"]):
            return "system_control"
        if any(w in t for w in ["shutdown", "shut down", "restart", "reboot", "sleep", "lock screen", "log off"]):
            return "system_power"
        if (any(w in t for w in ["kill", "terminate", "end", "close", "stop"])
                and any(w in t for w in ["process", "app", "program", "task"])):
            return "system_control"
        if any(w in t for w in ["running apps", "running processes", "list processes",
                                  "show processes", "what's running", "active apps"]):
            return "process_list"
        if re.search(r'\b(cpu|ram|memory usage|disk space|system info|battery|charge level|storage)\b', t):
            return "system_info"

        # ── Open app or website ──
        open_match = re.search(r'\b(open|launch|start|run|go to|take me to|show me)\b', t)
        if open_match:
            # Extract what to open
            after = t[open_match.end():].strip()
            # Remove "in browser/chrome/edge" suffix for intent detection
            clean = re.sub(r'\b(in (browser|chrome|firefox|edge|brave)|on the web|online)\b', '', after).strip()
            # Check if it's a known browser app
            for app_name in BROWSER_APPS:
                if app_name in clean or app_name in t:
                    return "open_browser_app"
            # Check for URL
            if re.search(r'\b(\.com|\.co\.uk|\.org|\.net|http)\b', clean):
                return "open_url"
            return "open_app"

        # ── Install app ──
        if re.search(r'\b(install|download|get)\b', t) and not re.search(r'\b(install it|install that)\b', t):
            app = re.sub(r'.*?\b(install|download|get)\b\s*', '', t).strip()
            app = re.sub(r'^(me |please |now |the |a )\b', '', app).strip()
            if app and len(app) >= 2:
                # Check if it's a browser app
                for app_name in BROWSER_APPS:
                    if app_name in app:
                        return "install_browser_app"
                return "store_install"

        # ── Weather / News / Web ──
        if any(w in t for w in ["weather", "temperature", "forecast", "raining", "sunny", "cloudy"]):
            return "weather"
        if any(w in t for w in ["news", "headlines", "what's happening", "latest news"]):
            return "news"
        if any(w in t for w in ["search youtube", "find video on youtube", "youtube search"]):
            return "youtube_search"
        if any(w in t for w in ["search for", "search ", "look up", "google ", "find out about", "browse"]):
            return "web_search"

        # ── Devices / Security ──
        if any(w in t for w in ["usb", "bluetooth", "external drive", "connected devices", "list devices"]):
            return "devices"
        if any(w in t for w in ["scan", "antivirus", "virus", "malware", "shield", "quarantine", "security scan", "check security", "am i safe"]):
            return "security"

        # ── Store ──
        if any(w in t for w in ["app store", "matcha store", "available apps", "what apps can", "what can i install", "show apps"]):
            return "store_browse"
        if any(w in t for w in ["uninstall", "remove app", "delete app"]):
            return "store_uninstall"

        # ── File management ──
        if any(w in t for w in ["find file", "search file", "where is my file", "open folder"]):
            return "file_management"

        # ── Productivity ──
        if any(w in t for w in ["remind me", "set reminder", "set alarm", "alarm in"]):
            return "reminder_set"
        if any(w in t for w in ["my reminders", "show reminders", "list reminders", "what are my reminders"]):
            return "reminder_list"
        if any(w in t for w in ["take a note", "save a note", "write a note", "note down", "note this", "make a note"]):
            return "note_add"
        if any(w in t for w in ["my notes", "show notes", "list notes", "show my notes"]):
            return "note_list"
        if any(w in t for w in ["clipboard", "clipboard history", "show clipboard"]):
            return "clipboard"

        # ── Contacts / Calls ──
        if any(w in t for w in ["add contact", "save contact", "new contact"]):
            return "contact_add"
        if any(w in t for w in ["my contacts", "show contacts", "list contacts"]):
            return "contacts"
        if any(w in t for w in ["make a video call", "video call", "video chat", "start a call",
                                  "call ", "ring "]) and not "recall" in t:
            return "call"

        # ── Identity ──
        if any(w in t for w in ["who are you", "what are you", "your name", "what can you do",
                                  "what do you do", "tell me about yourself", "introduce yourself"]):
            return "identity"

        # ── Greeting ──
        if re.search(r'^(hi|hello|hey|howdy|yo)\b', t) or any(w in t for w in [
                "good morning", "good evening", "good afternoon", "good night"]):
            return "greeting"

        # ── Everything else → brain ──
        return "general"

    def _handle_intent(self, intent: str, text: str) -> str:
        """Handle each intent type."""
        hour = datetime.datetime.now().hour
        t = text.lower().strip()

        # ── Greeting ──────────────────────────────────────────────────────────────
        if intent == "greeting":
            if self._brain and self.online:
                return self._reason(text)
            name = self.user_name if self.user_name != "User" else ""
            suffix = f", {name}" if name else ""
            if hour < 12:
                return f"Morning{suffix}. What do you need?"
            elif hour < 17:
                return f"Hey{suffix}. What can I do for you?"
            else:
                return f"Evening{suffix}. What do you need?"

        # ── Identity ──────────────────────────────────────────────────────────────
        elif intent == "identity":
            if self._brain and self.online:
                return self._reason(text)
            return (
                "MATCHA OS — your AI operating system. "
                "I can answer anything, write code, control your system, "
                "check weather, set reminders, open apps, and more. What do you need?"
            )

        # ── Open browser app (YouTube, Gmail, etc.) ──────────────────────────────
        elif intent == "open_browser_app":
            app_name = self._extract_open_target(text)
            app_lower = app_name.lower()
            url = None
            for key, val in BROWSER_APPS.items():
                if key in app_lower or key in t:
                    url = val
                    app_name = key.title()
                    break
            if url:
                # Ask permission
                if self._perms:
                    perm = self._perms.needs_permission(
                        "open_browser", app_name,
                        {"url": url, "label": app_name}
                    )
                    if perm.get("ask"):
                        msg = perm["message"]
                        if perm.get("can_remember"):
                            msg += "\n(Say 'yes always' to never ask again for opening websites)"
                        return msg
                return f"__OPEN_URL__{url}__LABEL__{app_name}"
            return self._reason(text)

        # ── Open URL directly ─────────────────────────────────────────────────────
        elif intent == "open_url":
            target = self._extract_open_target(text)
            if not target.startswith("http"):
                target = "https://" + target
            if self._perms:
                perm = self._perms.needs_permission(
                    "open_browser", target,
                    {"url": target, "label": target}
                )
                if perm.get("ask"):
                    return perm["message"]
            return f"__OPEN_URL__{target}__LABEL__{target}"

        # ── Open desktop app ──────────────────────────────────────────────────────
        elif intent == "open_app":
            app_name = self._extract_open_target(text)
            app_lower = app_name.lower()

            # Check browser apps first
            for key, url in BROWSER_APPS.items():
                if key in app_lower:
                    if self._perms:
                        perm = self._perms.needs_permission(
                            "open_browser", key.title(),
                            {"url": url, "label": key.title()}
                        )
                        if perm.get("ask"):
                            return perm["message"]
                    return f"__OPEN_URL__{url}__LABEL__{key.title()}"

            # Ask permission for desktop app
            if self._perms and app_name:
                perm = self._perms.needs_permission(
                    "open_app", app_name,
                    {"app": app_name}
                )
                if perm.get("ask"):
                    msg = perm["message"]
                    if perm.get("can_remember"):
                        msg += "\n(Say 'yes always' to always launch apps without asking)"
                    return msg

            # No permissions or already allowed — execute
            sc = self._get_system_control()
            if sc and app_name:
                result = sc.launch_app(app_name)
                if result.get("success"):
                    return result.get("summary", f"Launching {app_name}.")
                return f"'{app_name}' isn't installed. Want me to search for it online or open a web version?"
            return "Which application would you like to open?"

        # ── Install browser app ───────────────────────────────────────────────────
        elif intent == "install_browser_app":
            app = re.sub(r'.*?\b(install|download|get)\b\s*', '', t).strip()
            for key, url in BROWSER_APPS.items():
                if key in app:
                    if self._perms:
                        perm = self._perms.needs_permission(
                            "open_browser", f"{key.title()} (web version)",
                            {"url": url, "label": key.title()}
                        )
                        if perm.get("ask"):
                            return perm["message"]
                    return f"__OPEN_URL__{url}__LABEL__{key.title()}"
            return self._reason(text)

        # ── Online: Weather ───────────────────────────────────────────────────────
        elif intent == "weather":
            if not self.online:
                return "Need an internet connection for weather. Enable online mode."
            agent = self._get_web_agent()
            if not agent:
                return "Web agent unavailable."
            result = agent.get_weather(self._extract_location(text) or "London")
            return result.get("summary") or result.get("error", "Weather unavailable.")

        # ── Online: News ──────────────────────────────────────────────────────────
        elif intent == "news":
            if not self.online:
                return "Need an internet connection for news."
            agent = self._get_web_agent()
            if not agent:
                return "Web agent unavailable."
            result = agent.get_news("bbc")
            return result.get("summary") or result.get("error", "News unavailable.")

        # ── Online: YouTube search ────────────────────────────────────────────────
        elif intent == "youtube_search":
            if not self.online:
                return "Need online mode for YouTube search."
            agent = self._get_web_agent()
            if not agent:
                return "Web agent unavailable."
            query = self._strip_prefixes(text, ["search youtube for", "find video on youtube", "youtube search for", "youtube"])
            result = agent.search_youtube(query or text)
            return result.get("summary") or result.get("error", "YouTube search failed.")

        # ── Online: Web Search ────────────────────────────────────────────────────
        elif intent == "web_search":
            if not self.online:
                return "Need online mode for web search."
            agent = self._get_web_agent()
            if not agent:
                return "Web agent unavailable."
            query = self._strip_prefixes(text, ["search for", "search", "look up", "google", "find out"])
            result = agent.search(query or text)
            return result.get("summary") or result.get("error", "Search failed.")

        # ── System: Control ───────────────────────────────────────────────────────
        elif intent == "system_control":
            sc = self._get_system_control()
            if not sc:
                return "System control unavailable."
            result = sc.handle_command(text)
            return result.get("summary") or result.get("error", "Command failed.")

        # ── System: Power ─────────────────────────────────────────────────────────
        elif intent == "system_power":
            return self._handle_power(text)

        # ── System: Info ──────────────────────────────────────────────────────────
        elif intent == "system_info":
            sc = self._get_system_control()
            if not sc:
                return "System control unavailable."
            result = sc.get_system_info()
            return result.get("summary") or result.get("error", "System info unavailable.")

        elif intent == "process_list":
            sc = self._get_system_control()
            if not sc:
                return "System control unavailable."
            result = sc.list_processes()
            return result.get("summary") or "Could not fetch process list."

        # ── Open App ──────────────────────────────────────────────────────────────
        # (handled above in open_app branch)

        # ── File Management ───────────────────────────────────────────────────────
        elif intent == "file_management":
            sc = self._get_system_control()
            if not sc:
                return "File search unavailable."
            query = self._strip_prefixes(text, ["find file", "find", "search for", "where is", "locate"])
            result = sc.find_files(query or text)
            return result.get("summary") or result.get("error", "File search failed.")

        # ── Devices ───────────────────────────────────────────────────────────────
        elif intent == "devices":
            dm = self._get_device_manager()
            if not dm:
                return "Device manager unavailable."
            result = dm.handle_command(text)
            return result.get("summary") or result.get("error", "Device info unavailable.")

        # ── Security ──────────────────────────────────────────────────────────────
        elif intent == "security":
            return self._handle_security(text)

        # ── Calls ─────────────────────────────────────────────────────────────────
        elif intent == "call":
            calls = self._get_calls()
            if calls:
                video = "video" in text.lower()
                name = re.sub(r'\b(can you\s+)?(make\s+a\s+)?(video\s+)?(call|phone|ring|contact)\b', '', text, flags=re.I).strip()
                name = re.sub(r'^(please|me|a|an|the)\b\s*', '', name, flags=re.I).strip(' ?.,!')
                if not name or len(name) < 2:
                    return "Who do you want to call? Give me a name."
                return calls.initiate_call(name, video=video)
            return "Calling unavailable."

        elif intent == "contact_add":
            calls = self._get_calls()
            if calls:
                m = re.search(r'add (.+?) (?:with|number|email|contact)\s+(.+)', text, re.I)
                if m:
                    return calls.add_contact(m.group(1).strip(), m.group(2).strip())
            return "Say: 'Add [name] with number [number]'."

        elif intent == "contacts":
            calls = self._get_calls()
            return calls.list_contacts() if calls else "Contacts unavailable."

        # ── MATCHA Store ──────────────────────────────────────────────────────────
        elif intent == "store_install":
            store = self._get_store()
            if store:
                app = re.sub(r'\b(can you\s+)?(please\s+)?(install|download|get)\b', '', text, flags=re.I).strip()
                app = re.sub(r'\bfor me\b|\bplease\b|\bnow\b', '', app, flags=re.I).strip()
                app = app.strip(' ?.,!')
                if not app or len(app) < 2:
                    return "Which app should I install? Try: install Spotify, install Chrome, install VS Code."
                return store.install(app)
            return "MATCHA Store unavailable."

        elif intent == "store_browse":
            store = self._get_store()
            return store.list_catalogue() if store else "MATCHA Store unavailable."

        elif intent == "store_uninstall":
            store = self._get_store()
            if store:
                app = re.sub(r'uninstall|remove|delete', '', text, flags=re.I).strip()
                return store.uninstall(app) if app else "Which app should I remove?"
            return "MATCHA Store unavailable."

        # ── Productivity ──────────────────────────────────────────────────────────
        elif intent == "reminder_set":
            prod = self._get_productivity()
            if prod:
                m = re.search(r'remind me (?:to )?(.+?)(?:\s+(?:in|at|tomorrow)\s+.+)?$', text, re.I)
                task = m.group(1).strip() if m else text
                time_m = re.search(r'(in .+|at .+|tomorrow.+)$', text, re.I)
                when = time_m.group(1) if time_m else "in 1 hour"
                return prod.add_reminder(task, when)
            return "Reminders unavailable."

        elif intent == "reminder_list":
            prod = self._get_productivity()
            return prod.list_reminders() if prod else "Reminders unavailable."

        elif intent == "note_add":
            prod = self._get_productivity()
            if prod:
                content = re.sub(
                    r'\b(take a note|save a note|write a note|note down|note this|make a note|take note|save note|write note)\b',
                    '', text, flags=re.I).strip()
                content = re.sub(r'^[:\-\s]+', '', content).strip()
                if not content or len(content) < 2:
                    return "What should I note down?"
                title = content[:40] + "..." if len(content) > 40 else content
                return prod.add_note(title, content)
            return "Notes unavailable."

        elif intent == "note_list":
            prod = self._get_productivity()
            return prod.list_notes() if prod else "Notes unavailable."

        elif intent == "clipboard":
            prod = self._get_productivity()
            return prod.list_clipboard() if prod else "Clipboard history unavailable."

        # ── General — Brain handles everything ───────────────────────────────────
        else:
            return self._reason(text)

    def _handle_power(self, text: str) -> str:
        """Handle power commands with confirmation gate."""
        text_lower = text.lower()
        if "confirm" in text_lower or "yes" in text_lower:
            sc = self._get_system_control()
            if sc:
                if "shutdown" in text_lower or "shut down" in text_lower:
                    return sc.shutdown().get("summary", "Shutdown initiated.")
                elif "restart" in text_lower or "reboot" in text_lower:
                    return sc.restart().get("summary", "Restarting.")
        else:
            if "shutdown" in text_lower or "shut down" in text_lower:
                return "Say 'confirm shutdown' to proceed."
            elif "restart" in text_lower or "reboot" in text_lower:
                return "Say 'confirm restart' to proceed."
            elif "sleep" in text_lower:
                sc = self._get_system_control()
                if sc:
                    return sc.sleep().get("summary", "System sleeping.")
            elif "lock" in text_lower:
                sc = self._get_system_control()
                if sc:
                    return sc.lock_screen().get("summary", "Screen locked.")
        return "Power command not recognised."

    def _handle_security(self, text: str) -> str:
        """Handle security commands."""
        text_lower = text.lower()
        shield = self._get_shield()
        if not shield:
            return "MATCHA Shield unavailable."

        if "status" in text_lower:
            return shield.get_status().get("summary", "Shield status unavailable.")
        elif "scan" in text_lower:
            import re
            match = re.search(r'scan (.+)', text_lower)
            path = match.group(1).strip() if match else str(Path.home() / "Downloads")
            return f"Scanning {path}. This may take a moment."
        elif "quarantine" in text_lower:
            return shield.list_quarantine().get("summary", "Quarantine empty.")
        elif "threats" in text_lower or "log" in text_lower:
            return shield.get_threat_log(5).get("summary", "No threats logged.")
        else:
            return shield.get_status().get("summary", "Shield active.")

    # ── Lazy Loaders ─────────────────────────────────────────────────────────────

    def _get_store(self):
        if not hasattr(self, '_store') or self._store is None:
            try:
                from core.store.matcha_store import MatchaStore
                self._store = MatchaStore()
            except Exception as e:
                print(f"[MATCHA] Store load failed: {e}")
                self._store = None
        return self._store

    def _get_calls(self):
        if not hasattr(self, '_calls') or self._calls is None:
            try:
                from core.calls.matcha_calls import MatchaCalls
                self._calls = MatchaCalls()
            except Exception as e:
                print(f"[MATCHA] Calls load failed: {e}")
                self._calls = None
        return self._calls

    def _get_productivity(self):
        if not hasattr(self, '_productivity') or self._productivity is None:
            try:
                from core.productivity.matcha_productivity import MatchaProductivity
                self._productivity = MatchaProductivity(alert_callback=self._on_reminder)
            except Exception as e:
                print(f"[MATCHA] Productivity load failed: {e}")
                self._productivity = None
        return self._productivity

    def _on_reminder(self, alert_type: str, message: str):
        print(f"[MATCHA] ⏰ Reminder: {message}")

    def _get_web_agent(self):
        if self._web_agent is None:
            self._load_web_agent()
        return self._web_agent

    def _get_thinker(self):
        if self._thinker is None:
            try:
                from core.online.thinker import Thinker
                self._thinker = Thinker()
                print("[MATCHA] Thinker loaded.")
            except Exception as e:
                print(f"[MATCHA] Thinker failed: {e}")
        return self._thinker

    def _get_system_control(self):
        if self._system_control is None:
            self._load_system_control()
        return self._system_control

    def _get_device_manager(self):
        if self._device_manager is None:
            self._load_device_manager()
        return self._device_manager

    def _get_shield(self):
        if self._shield is None:
            self._load_shield()
        return self._shield

    # ── Helpers ──────────────────────────────────────────────────────────────────

    def _extract_open_target(self, text: str) -> str:
        """Extract what to open from a command."""
        t = text.lower()
        # Remove "in browser/chrome/etc" suffix
        t = re.sub(r'\b(in (browser|chrome|firefox|edge|brave|a browser|the browser)|on the web|online|in browser)\b', '', t).strip()
        for word in ["open", "launch", "start", "run", "go to", "take me to", "show me"]:
            if word in t:
                parts = t.split(word, 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return text.strip()

    def _extract_location(self, text: str) -> str:
        """Extract location from text."""
        patterns = [
            r'weather (?:in|for|at) ([A-Za-z\s]+)',
            r'(?:in|at|for) ([A-Za-z\s]+) weather',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _strip_prefixes(self, text: str, prefixes: list) -> str:
        """Strip known command prefixes from query."""
        text_lower = text.lower()
        for prefix in prefixes:
            if prefix in text_lower:
                return text_lower.split(prefix, 1)[-1].strip()
        return text

    def _reason(self, text: str) -> str:
        """Primary reasoning — Groq brain first, local knowledge, web thinker fallback."""
        # 0. Check local learned knowledge first (fast, free)
        if self._learner and self.online:
            local_knowledge = self._learner.recall(text)
            if local_knowledge and len(local_knowledge) > 20:
                # Enhance with brain if available
                if self._brain:
                    try:
                        ctx = f"Known fact: {local_knowledge}\nAnswer the user's question using this and your own knowledge."
                        answer = self._brain.think(text, system_context=ctx)
                        if answer and len(answer) > 2:
                            # Store improved answer
                            self._learner.learn_and_store(
                                self._learner._extract_topic(text), answer[:500], "groq_enhanced"
                            )
                            return answer
                    except Exception:
                        pass
                return local_knowledge

        # 1. Groq brain — real intelligence (if available)
        if self.online and self._brain:
            try:
                import datetime as _dt
                ctx = f"Time: {_dt.datetime.now().strftime('%H:%M, %d %b %Y')}. User: {self.user_name}."
                answer = self._brain.think(text, system_context=ctx)
                if answer and len(answer) > 2:
                    # Self-learn from brain's answer
                    if self._learner:
                        try:
                            topic = self._learner._extract_topic(text)
                            self._learner.learn_and_store(topic, answer[:500], "groq_brain")
                            # Check if user has asked this 3+ times — deepen knowledge
                            self._learner._track_interest(topic)
                            interests = dict(self._learner.get_top_interests(20))
                            if interests.get(topic, 0) >= 3:
                                self._learner.deepen_knowledge(topic)
                        except Exception:
                            pass
                    return answer
            except Exception:
                pass

        # 2. Known patterns (instant OS commands)
        result = self._retriever_predict(text)
        if result:
            return result

        # 3. Web thinker fallback
        if self.online:
            try:
                thinker = self._get_thinker()
                if thinker:
                    answer = thinker.think(text)
                    if answer and len(answer) > 10:
                        # Learn this too
                        if self._learner:
                            try:
                                self._learner.learn_and_store(
                                    self._learner._extract_topic(text), answer[:500], "web_thinker"
                                )
                            except Exception:
                                pass
                        return answer
            except:
                pass

        return "I need an internet connection to answer that. Connect and try again."

    def get_learning_stats(self) -> str:
        """Return what MATCHA has learned so far."""
        if not self._learner:
            return "Learning engine not available."
        stats = self._learner.get_stats()
        top = ", ".join([f"{t} ({c}x)" for t, c in stats["top_topics"][:5]])
        return (
            f"I've learned {stats['total_facts']} facts across {stats['total_topics']} topics. "
            f"Your top interests: {top or 'none yet'}."
        )

    def get_permissions(self) -> str:
        """Return current always-allow permissions."""
        if not self._perms:
            return "Permission manager not available."
        allowed = self._perms.get_always_allowed()
        if not allowed:
            return "No 'always allow' permissions set. I'll ask before every action."
        lines = [f"• {a[0].replace('_', ' ').title()} (since {a[1][:10]})" for a in allowed]
        return "Always allowed:\n" + "\n".join(lines)

    def revoke_permission(self, action_type: str) -> str:
        """Revoke an always-allow permission."""
        if self._perms:
            self._perms.revoke_always_allow(action_type)
            return f"Permission revoked. I'll ask before {action_type.replace('_', ' ')} from now on."
        return "Permission manager unavailable."
        """What MATCHA says when the OS starts."""
        hour = datetime.datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        mode = "Online" if self.online else "Local Mode"
        greeting = f"{time_greeting}, {self.user_name}. MATCHA is ready. Running in {mode}."

        suggestion = self.memory.get_proactive_suggestion(hour)
        if suggestion:
            greeting += f" {suggestion}"

        return greeting


class MatchaMemory:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input TEXT,
                intent TEXT,
                response TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                hour INTEGER,
                action TEXT,
                count INTEGER DEFAULT 1,
                PRIMARY KEY (hour, action)
            )
        """)
        self.conn.commit()

    def log_interaction(self, user_input: str, intent: str = "", response: str = ""):
        self.conn.execute(
            "INSERT INTO interactions (timestamp, input, intent, response) VALUES (?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(), user_input, intent, response)
        )
        hour = datetime.datetime.now().hour
        if intent:
            self.conn.execute("""
                INSERT INTO patterns (hour, action, count) VALUES (?, ?, 1)
                ON CONFLICT(hour, action) DO UPDATE SET count = count + 1
            """, (hour, intent))
        self.conn.commit()

    def get_recent_context(self, limit: int = 10) -> list:
        cursor = self.conn.execute(
            "SELECT input, intent, response FROM interactions ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()

    def get_last_session_summary(self) -> str:
        cursor = self.conn.execute(
            "SELECT input FROM interactions ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        return f"last request was '{row[0]}'" if row else ""

    def get_proactive_suggestion(self, hour: int) -> str:
        try:
            cursor = self.conn.execute(
                "SELECT action, count FROM patterns WHERE hour = ? ORDER BY count DESC LIMIT 1",
                (hour,)
            )
            row = cursor.fetchone()
            if row and row[1] >= 3:
                action = row[0]
                suggestions = {
                    "news": "You usually check the news at this time. Say 'news' to get headlines.",
                    "weather": "You usually check the weather now. Want today's forecast?",
                    "web_search": "Anything you'd like to search for today?",
                    "greeting": None,
                    "schedule": "You usually check your schedule at this time. Ready to review.",
                    "media": "Your music is ready when you are.",
                }
                return suggestions.get(action, "")
        except Exception:
            pass
        return ""

    def set_preference(self, key: str, value: str):
        self.conn.execute("""
            INSERT INTO preferences (key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
        """, (key, value, datetime.datetime.now().isoformat(),
              value, datetime.datetime.now().isoformat()))
        self.conn.commit()

    def get_preference(self, key: str, default=None):
        cursor = self.conn.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else default

    def get_patterns(self) -> dict:
        cursor = self.conn.execute(
            "SELECT hour, action, count FROM patterns ORDER BY count DESC"
        )
        patterns = {}
        for hour, action, count in cursor.fetchall():
            if hour not in patterns:
                patterns[hour] = []
            patterns[hour].append((action, count))
        return patterns


class MatchaPersonality:
    """
    Formats all responses in MATCHA's voice.
    Calm. Precise. Confident. Like Jarvis.
    """

    def format(self, response: str, intent: str = "") -> str:
        filler = [
            "Certainly!", "Of course!", "Sure!", "Absolutely!",
            "Great question!", "I'd be happy to", "I can help with that",
            "No problem!", "Of course,", "Happy to help",
        ]
        for f in filler:
            response = response.replace(f, "")

        response = response.strip()

        if response and response[-1] not in ".?!":
            response += "."

        return response


if __name__ == "__main__":
    ai = MatchaAI()
    ai.user_name = "Rohith"
    print(ai.greet_on_boot())
    print(ai.think("Hey MATCHA, who are you?"))
    ai.set_online(True)
    print(ai.think("What's the weather in London?"))
    print(ai.think("What's my CPU usage?"))
