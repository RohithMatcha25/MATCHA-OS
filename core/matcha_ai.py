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
import threading
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
        self._builder = None
        self._executor = None
        self._trainer = None
        self._evolution = None
        self._browser_agent = None
        self._persistent_memory = None
        self._init_brain()
        self._init_learner()
        self._init_perms()
        self._init_builder()
        self._init_executor()
        self._init_trainer()
        self._init_evolution()
        self._init_browser_agent()
        self._init_persistent_memory()
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

    def _init_builder(self):
        """Load the app builder."""
        try:
            from core.builder.matcha_builder import MatchaBuilder
            self._builder = MatchaBuilder()
        except Exception as e:
            print(f"[MATCHA] Builder unavailable: {e}")
            self._builder = None

    def _init_executor(self):
        """Load the code executor."""
        try:
            from core.executor.matcha_executor import MatchaExecutor
            self._executor = MatchaExecutor()
        except Exception as e:
            print(f"[MATCHA] Executor unavailable: {e}")
            self._executor = None

    def _init_trainer(self):
        """Load the self-training engine."""
        try:
            from core.trainer.matcha_trainer import MatchaTrainer
            self._trainer = MatchaTrainer()
        except Exception as e:
            print(f"[MATCHA] Trainer unavailable: {e}")
            self._trainer = None

    def _init_evolution(self):
        """Load the evolution engine."""
        try:
            from core.evolution.matcha_evolution import MatchaEvolution
            self._evolution = MatchaEvolution()
            if self.online:
                seed_topics = [
                    "artificial intelligence", "machine learning", "python programming",
                    "web development", "data science", "cloud computing", "cybersecurity"
                ]
                self._evolution.start_background_crawl(seed_topics)
        except Exception as e:
            print(f"[MATCHA] Evolution unavailable: {e}")
            self._evolution = None

    def _init_browser_agent(self):
        """Load the browser automation agent."""
        try:
            from core.browser.matcha_browser import MatchaBrowserAgent
            self._browser_agent = MatchaBrowserAgent()
        except Exception as e:
            print(f"[MATCHA] Browser agent unavailable: {e}")
            self._browser_agent = None

    def _init_persistent_memory(self):
        """Load persistent cross-session memory."""
        try:
            from core.memory_persistent.matcha_memory_persistent import MatchaMemoryPersistent
            self._persistent_memory = MatchaMemoryPersistent()
        except Exception as e:
            print(f"[MATCHA] Persistent memory unavailable: {e}")
            self._persistent_memory = None

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

        # Log to persistent memory
        if self._persistent_memory:
            try:
                self._persistent_memory.log_conversation("user", user_input)
            except Exception:
                pass

        # Update conversation context
        self._conversation_context.append({"role": "user", "text": user_input, "intent": intent})

        # Route to handler
        response = self._handle_intent(intent, user_input)

        # Apply MATCHA personality
        response = self.personality.format(response, intent)

        # If response is an OPEN_URL, NEED_CREDS or ASK_PERMISSION — return as-is
        if (response.startswith("__OPEN_URL__") or
            response.startswith("__ASK_PERMISSION__") or
            response.startswith("__NEED_CREDS__") or
            response.startswith("__BUILD__ASYNC__")):
            return response

        # Log response
        self._conversation_context.append({"role": "matcha", "text": response})

        # Log to persistent memory
        if self._persistent_memory:
            try:
                self._persistent_memory.log_conversation("matcha", response)
            except Exception:
                pass

        # Self-learn
        if self._learner and self.online and intent == "general":
            try:
                self._learner.learn_and_store(
                    topic=self._learner._extract_topic(user_input),
                    fact=response[:500],
                    source="brain"
                )
            except Exception:
                pass

        # Log to trainer
        if self._trainer:
            try:
                self._trainer.log(user_input, response, intent)
            except Exception:
                pass

        # Evolution background crawl
        if self._evolution and self.online and intent == "general":
            try:
                threading.Thread(
                    target=self._evolution.learn_from_web,
                    args=(user_input[:60],), daemon=True
                ).start()
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

        # ══ HARD INTERCEPTS — never reach Groq ═══════════════════════════════

        # Credential saving — catches typos: passwrod, passw, passwd
        _cred_kws = ["username is", "user name is", "password is", "passwrod is",
                     "passw is", "passwd is", "my email is", "login is",
                     "save my credentials", "store my login"]
        _has_email = any(c in t for c in ["@", ".com", ".co.uk"])
        if any(w in t for w in _cred_kws) or (_has_email and any(
                w in t for w in ["username", "password", "passwrod", "login", "email"])):
            return "save_credentials"

        # Browser tasks — service + action keyword
        _svcs = ["linkedin", "instagram", "insta", "github", "git repo", "my repo",
                 "gmail", "google mail", "amazon", "twitter", "facebook",
                 "deliveroo", "uber eats", "ubereats", "just eat",
                 "netflix", "spotify", "my profile", "my account"]
        _acts = ["login", "log in", "log into", "sign in", "open my", "access my",
                 "go to my", "check my", "update my", "apply", "order",
                 "post on", "message on", "search on", "find jobs",
                 "apply jobs", "apply to jobs", "start applying"]
        if any(s in t for s in _svcs) and any(a in t for a in _acts):
            return "browser_task"

        # Task / status questions
        if t.startswith("did you") or t.startswith("have you") or t.startswith("are you applying"):
            return "task_status"

        # Credential check
        if any(w in t for w in ["do you have my", "did you save my", "my credentials",
                                 "have you got my", "saved my creds"]):
            return "credential_check"

        # ══ End hard intercepts ═══════════════════════════════════════════════

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
        if re.search(r'\b(cpu|ram|memory usage|disk space|system info|battery|charge level|storage|whoami|computer name|hostname|system user)\b', t):
            return "system_info"
        # username/user name only if asking about it, not providing it
        if re.search(r'\b(my username|what is my username|show username|get username|system username)\b', t) and "is " not in t:
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

        # ── Build / create app ──
        # ONLY trigger when user explicitly asks to BUILD something
        # "can you build" / "can you make" = capability question → goes to brain
        # Must have BOTH: an action phrase ("build me", "make me") AND a target ("app", "website")
        # AND must NOT start with "can you" (capability question)
        if not t.startswith("can you") and not t.startswith("could you") and not t.startswith("do you"):
            build_triggers = ["build me", "create me", "make me", "develop me",
                              "build a ", "create a ", "make a ", "develop a ",
                              "code me a", "write me a", "i want you to build",
                              "make an ", "build an ", "create an "]
            build_targets = ["app", "website", "web app", "webapp", "tool", "dashboard",
                             "todo", "calculator", "game", "chat app", "portfolio", "landing page",
                             "api", "backend", "frontend", "full stack", "quiz", "timer",
                             "weather app", "notes app", "blog", "store", "shop", "tracker"]
            if any(bt in t for bt in build_triggers) and any(tg in t for tg in build_targets):
                return "build_app"

        # ── Run / execute code ──
        if any(w in t for w in ["run this", "execute this", "run the code", "execute code",
                                  "run code", "test this code"]):
            return "run_code"

        # ── Self-evolve / evolve yourself — honest handler ──
        if any(w in t for w in ["evolve yourself", "self evolve", "self-evolve",
                                  "evolve itself", "rewrite your", "update your weights",
                                  "update your training", "retrain yourself", "improve yourself",
                                  "self improve", "self-improve", "modify yourself",
                                  "upgrade yourself", "do it", "do it yourself"]):
            return "self_evolve_request"

        # ── Self-train intent model from usage data ──
        if any(w in t for w in ["retrain", "update your model", "self train", "self-train",
                                  "train yourself"]):
            return "self_retrain"

        # ── Learn about a topic from web ──
        if any(w in t for w in ["learn about", "research", "study", "find out about",
                                  "what do you know about"]):
            return "evolve_learn"

        # ── What have you learned / evolution stats ──
        if any(w in t for w in ["what have you learned", "what do you know", "your knowledge",
                                  "evolution stats", "learning stats", "how smart are you"]):
            return "evolution_stats"

        # ── List running apps ──
        if any(w in t for w in ["list apps", "running apps", "what apps", "show apps", "my apps"]):
            return "list_apps"

        # ── Stop app ──
        if any(w in t for w in ["stop app", "kill app", "close app", "shut down app"]):
            return "stop_app"

        # ── Media / music ──
        if any(w in t for w in ["play music", "play songs", "play spotify", "music player",
                                  "open spotify", "play something"]):
            return "media_play"

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
        if any(w in t for w in ["list files", "list folders", "list the folders", "list my folders",
                                  "files in", "what files", "show files", "files list", "folder list",
                                  "my downloads", "my documents", "my desktop", "my pictures",
                                  "list my", "what's in my", "whats in my", "show my folders",
                                  "what folders", "show folders", "my folders", "folders in my",
                                  "list the files", "show the files", "list all files", "list all folders"]):
            return "file_list"

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
                                  "what do you do", "tell me about yourself", "introduce yourself",
                                  "your features", "your capabilities", "what else can you do"]):
            return "identity"

        # ── Task status — MUST be before browser_task ──
        if t.startswith("did you") or t.startswith("have you") or any(
            w in t for w in ["task status", "task progress", "background tasks",
                              "did you complete", "did you finish", "what happened with",
                              "is it done", "any updates"]):
            return "task_status"

        # ── Save credentials — MUST be before browser_task ──
        if (any(w in t for w in ["username is", "password is", "my email is",
                                   "save my credentials", "store my login"]) and
                any(c in t for c in ["@", "password", "pass"])):
            return "save_credentials"

        # ── Browser automation / web tasks ──
        browser_services = ["linkedin", "instagram", "insta", "github", "gmail", "amazon",
                            "twitter", "facebook", "uber", "deliveroo", "just eat", "ubereats",
                            "youtube", "netflix", "spotify", "whatsapp", "telegram"]
        browser_actions = ["login", "log in", "sign in", "open my", "access my", "go to my",
                           "check my", "update my", "apply for", "order", "post on", "message on",
                           "search on", "find jobs on", "upload to"]
        if any(svc in t for svc in browser_services) and any(act in t for act in browser_actions):
            return "browser_task"
        if any(w in t for w in ["login to", "log into", "sign into", "access my account"]):
            return "browser_task"

        # ── Persistent memory ──
        if any(w in t for w in ["remember that", "remember this", "don't forget", "keep this in mind",
                                  "save this", "note that", "store this"]):
            return "memory_store"
        if any(w in t for w in ["what do you remember", "what do you know about me",
                                  "my memories", "recall", "what have i told you",
                                  "show my memories", "forget that", "forget this"]):
            return "memory_recall"

        # ── Task status ──
        if any(w in t for w in ["task status", "what are you doing", "any updates",
                                  "task progress", "background tasks"]):
            return "task_status"

        # ── Credential questions — MUST intercept before brain ──
        if any(w in t for w in ["do you have my", "did you save", "my credentials",
                                  "do you know my", "my linkedin", "my instagram",
                                  "my github", "my gmail", "my password", "my login",
                                  "saved my", "have you got my"]):
            return "credential_check"

        # ── Task status questions ──
        if any(w in t for w in ["did you login", "did you do it", "what happened",
                                  "any update", "is it done", "have you logged",
                                  "did you complete", "what did you do", "status"]):
            return "task_status"

        # ── Brain/AI mode ──
        if any(w in t for w in ["install ollama", "setup ollama", "local ai",
                                  "which ai", "your ai model"]):
            return "brain_info"

        # ── Capability questions — answer instantly without Groq ──
        if t.startswith("can you ") or t.startswith("could you ") or t.startswith("do you "):
            return "capability_question"

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
            name = self.user_name if self.user_name != "User" else ""
            if hour < 12:
                return f"Morning{', ' + name if name else ''}. What do you need?"
            elif hour < 17:
                return f"Hey{', ' + name if name else ''}. What can I do for you?"
            else:
                return f"Evening{', ' + name if name else ''}. What do you need?"

        # ── Identity ──────────────────────────────────────────────────────────────
        elif intent == "identity":
            return (
                "MATCHA - your local AI OS. I run on your machine, answer questions, "
                "open apps, control your system, build real apps, and get smarter over time."
            )

        # ── Browser Task ──────────────────────────────────────────────────────────
        elif intent == "browser_task":
            t_lower = text.lower()

            # ── Detect service key ────────────────────────────────────────────
            SERVICE_MAP = {
                "linkedin": "linkedin",
                "instagram": "instagram", "insta": "instagram",
                "github": "github", "git repo": "github", "my repo": "github", "git": "github",
                "gmail": "gmail", "google mail": "gmail",
                "amazon": "amazon",
                "twitter": "twitter", "x.com": "twitter",
                "facebook": "facebook", "fb": "facebook",
                "netflix": "netflix",
                "spotify": "spotify",
                "deliveroo": "deliveroo",
                "uber eats": "ubereats", "ubereats": "ubereats",
                "just eat": "just eat",
            }
            service_key = "web"
            for keyword, key in SERVICE_MAP.items():
                if keyword in t_lower:
                    service_key = key
                    break

            # ── Get credentials — always lowercase (that's how they're stored) ─
            creds = self._browser_agent.get_credentials(service_key.lower())

            if not creds:
                return (
                    f"I need your **{service_key.title()}** credentials to do this.\n\n"
                    f"Say: **my {service_key} username is email@x.com and password is yourpass**\n"
                    f"Credentials are saved only on your machine, never sent anywhere."
                )

            u, p = creds["username"], creds["password"]

            # ── Lazy-load universal agent ─────────────────────────────────────
            if not hasattr(self, '_universal_agent'):
                try:
                    from core.browser.universal_agent import UniversalBrowserAgent
                    self._universal_agent = UniversalBrowserAgent()
                except Exception as e:
                    return f"Browser agent failed to load: {e}"

            ua = self._universal_agent

            # ── LinkedIn Easy Apply (special case — long-running) ─────────────
            if service_key == "linkedin" and any(
                w in t_lower for w in ["apply to all", "apply for all", "auto apply",
                                        "apply jobs", "apply to jobs", "start applying",
                                        "apply related", "filter and apply"]
            ):
                # Load from user profile if available
                import json as _json, os as _os
                _profile_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "core", "memory", "user_profile.json")
                _profile = {}
                try:
                    if _os.path.exists(_profile_path):
                        _profile = _json.load(open(_profile_path))
                except Exception:
                    pass

                # Extract job titles from text, fall back to profile
                job_titles = []
                for jt in ["software engineer", "automation engineer", "backend",
                            "frontend", "full stack", "python developer", "devops",
                            "software developer", "data engineer"]:
                    if jt in t_lower:
                        job_titles.append(jt)
                if not job_titles:
                    job_titles = _profile.get("target_roles", ["Software Engineer"])[:3]

                # Extract locations from text, fall back to profile
                locations = []
                loc_map = {"uk": "United Kingdom", "united kingdom": "United Kingdom",
                           "scotland": "Scotland", "india": "India",
                           "london": "London", "england": "England"}
                for loc_kw, loc_name in loc_map.items():
                    if loc_kw in t_lower:
                        locations.append(loc_name)
                if not locations:
                    locations = _profile.get("target_locations", ["United Kingdom"])

                def _apply_all():
                    for jt in job_titles:
                        ua.linkedin_apply_all(u, p, query=jt, locations=locations)

                threading.Thread(target=_apply_all, daemon=True).start()
                return (
                    f"Starting LinkedIn Easy Apply:\n"
                    f"**Jobs:** {', '.join(job_titles)}\n"
                    f"**Locations:** {', '.join(locations)}\n\n"
                    f"Browser opening now. Takes 3-5 minutes per job title.\n"
                    f"Say **'did you apply?'** to check progress."
                )

            # ── All other tasks: universal run_task ───────────────────────────
            threading.Thread(
                target=lambda: ua.run_task(service_key, u, p, text),
                daemon=True
            ).start()

            # Friendly response
            action_desc = {
                "profile": "your profile",
                "jobs": "jobs",
                "messages": "your messages",
                "inbox": "your inbox",
                "orders": "your orders",
                "compose": "compose",
                "explore": "Explore",
            }
            action = "it"
            for kw, desc in action_desc.items():
                if kw in t_lower:
                    action = desc
                    break

            return (
                f"Opening **{service_key.title()}** and going to {action}.\n"
                f"Browser launching now — takes 10-20 seconds.\n"
                f"Say **'what happened?'** after the browser opens."
            )

        # ── Save Credentials ──────────────────────────────────────────────────────
        elif intent == "save_credentials":
            import re as _re
            t_orig = text
            t_lower = text.lower()

            # ── Detect service ────────────────────────────────────────────────
            service = "web"
            svc_map = {
                "linkedin": "linkedin", "instagram": "instagram", "insta": "instagram",
                "github": "github", "git": "github", "gmail": "gmail",
                "amazon": "amazon", "twitter": "twitter", "facebook": "facebook",
                "netflix": "netflix", "spotify": "spotify", "deliveroo": "deliveroo",
            }
            for kw, svc in svc_map.items():
                if kw in t_lower:
                    service = svc
                    break

            # ── Extract email/username ─────────────────────────────────────────
            # Priority 1: explicit "username is X" or "email is X"
            # Priority 2: bare email address anywhere in text
            user_match = (
                _re.search(r'(?:user\s*name|email|login)\s+is\s+([a-zA-Z0-9_.+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})', t_orig, _re.IGNORECASE) or
                _re.search(r'(?:user\s*name|email|login)\s+is\s+(\S+)', t_orig, _re.IGNORECASE) or
                _re.search(r'\b([a-zA-Z0-9_.+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\b', t_orig)
            )

            # ── Extract password — handles typos: passwrod, passw, passwd ─────
            # Must skip "is" as a value — the actual password follows "is" or ":"
            pwd_match = _re.search(
                r'pass\w*\s*(?:is\s+|[:\-]\s*)([^\s,]+)',
                t_orig, _re.IGNORECASE
            )
            # Ensure we didn't accidentally capture "is" itself
            if pwd_match and pwd_match.group(1).lower() == "is":
                pwd_match = _re.search(
                    r'pass\w*\s+is\s+(\S+)',
                    t_orig, _re.IGNORECASE
                )

            if user_match and pwd_match:
                username = user_match.group(1).strip().rstrip(".,")
                password = pwd_match.group(1).strip().rstrip(".,")

                if self._browser_agent:
                    self._browser_agent.store_credentials(service.lower(), username, password)
                if self._persistent_memory:
                    self._persistent_memory.remember("credentials", service, f"saved ({username})")

                return (
                    f"✅ **{service.title()} credentials saved** on your machine.\n\n"
                    f"Username: `{username}`\n\n"
                    f"Say: **login to my {service}** to use them."
                )

            # If only email found, ask for password
            if user_match:
                username = user_match.group(1).strip()
                return f"Got username `{username}`. What's the password for {service.title()}?"

            return (
                f"Couldn't extract credentials. Say exactly:\n\n"
                f"**my {service} username is email@x.com and password is yourpassword**"
            )

        # ── Memory Store ──────────────────────────────────────────────────────────
        elif intent == "memory_store":
            if self._persistent_memory:
                # Extract what to remember
                t_clean = text.lower()
                for phrase in ["remember that", "remember this", "don't forget", "keep this in mind",
                               "save this", "note that", "store this"]:
                    t_clean = t_clean.replace(phrase, "").strip()
                self._persistent_memory.remember("user_notes", t_clean[:100], t_clean)
                return f"Remembered: '{t_clean}' — stored locally and will persist across sessions."
            return "Persistent memory not available."

        # ── Memory Recall ─────────────────────────────────────────────────────────
        elif intent == "memory_recall":
            if self._persistent_memory:
                t_lower = text.lower()
                if "forget" in t_lower:
                    key = t_lower.replace("forget that", "").replace("forget this", "").strip()
                    return self._persistent_memory.forget(key)
                return self._persistent_memory.format_memories() or "Nothing stored yet."
            return "Persistent memory not available."

        # ── Task Status ───────────────────────────────────────────────────────────
        elif intent == "task_status":
            t_lower = text.lower()
            # Universal agent status
            if hasattr(self, '_universal_agent'):
                ua = self._universal_agent
                # Check for specific service
                for svc in ["linkedin", "instagram", "gmail", "github", "amazon"]:
                    if svc in t_lower:
                        return ua.get_status(svc)
                return ua.get_status()
            # LinkedIn legacy agent
            if hasattr(self, '_linkedin_agent'):
                return self._linkedin_agent.get_status()
            return "No browser tasks run yet. Say 'login to my linkedin' to start."

        elif intent == "credential_check":
            if not self._browser_agent:
                return "Browser agent not available."
            saved = self._browser_agent.list_saved_services()
            t_lower = text.lower()
            # Check specific service
            for svc in ["linkedin", "instagram", "github", "gmail", "amazon", "twitter"]:
                if svc in t_lower:
                    creds = self._browser_agent.get_credentials(svc)
                    if creds:
                        return f"Yes, I have your {svc.title()} credentials saved (username: {creds['username']}). Say 'login to my {svc}' to use them."
                    else:
                        return f"No credentials saved for {svc.title()} yet. Say: 'my {svc} username is email@x.com and password is yourpass'"
            # General check
            if saved:
                return f"I have credentials saved for: **{', '.join(saved)}**\n\nSay 'login to my [service]' to use them."
            return "No credentials saved yet. Say: 'my linkedin username is email@x.com and password is yourpass'"

        elif intent == "brain_info":
            if self._brain:
                mode = self._brain.get_mode()
                instructions = self._brain.install_instructions()
                return f"**Current AI brain:** {mode}\n\n{instructions}"
            return "Brain not loaded."


            t_lower = text.lower()
            # Map capability questions to direct answers
            caps = {
                ("code", "program", "programming"): "Yes - Python, JavaScript, HTML/CSS, React, Django, SQL, Bash. What do you need?",
                ("build", "create", "make", "develop"): "Yes. Tell me what you want - 'build me a todo app' and I'll write it, run it, and give you a URL.",
                ("website", "web app", "webapp"): "Yes. Give me the spec and I'll build the whole thing and run it locally.",
                ("self learn", "learn from web", "learn over time"): "Yes. I crawl Wikipedia and DuckDuckGo in the background and store facts locally. I get smarter over time.",
                ("evolve", "self evolve", "evolve yourself", "improve yourself"): "Not in the way you mean. I can't rewrite my own weights — no AI can. But I do learn from the web and from our conversations. Say 'retrain yourself' to update my intent model from usage.",
                ("remember", "memory"): "Within a session, yes. Across sessions, I store facts in a local database.",
                ("open", "launch", "run app"): "Yes. I can open any app or website on your machine.",
                ("system", "control", "os"): "Yes. I can check CPU/RAM/disk, open apps, control volume, list files, and more.",
                ("weather"): "Yes. Ask 'weather in [city]'.",
                ("news"): "Yes. Ask 'latest news'.",
                ("search"): "Yes. Ask me anything and I'll search the web.",
                ("voice", "speak", "talk"): "Yes. Click the mic button or say your message - I understand speech.",
            }
            for keywords, answer in caps.items():
                if isinstance(keywords, str):
                    if keywords in t_lower:
                        return answer
                else:
                    if any(k in t_lower for k in keywords):
                        return answer
            # Generic capability question
            return "Yes, most likely. Tell me what you need and I'll do it."


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

        elif intent == "file_list":
            import os, platform
            t_lower = text.lower()
            home = os.path.expanduser("~")
            # Determine which folder
            folder_map = {
                "downloads": os.path.join(home, "Downloads"),
                "documents": os.path.join(home, "Documents"),
                "desktop": os.path.join(home, "Desktop"),
                "pictures": os.path.join(home, "Pictures"),
                "music": os.path.join(home, "Music"),
                "videos": os.path.join(home, "Videos"),
            }
            target_dir = None
            target_name = "home"
            for name, path in folder_map.items():
                if name in t_lower:
                    target_dir = path
                    target_name = name.title()
                    break
            if not target_dir:
                target_dir = home
            try:
                if not os.path.exists(target_dir):
                    return f"Folder '{target_name}' not found on this system."
                entries = os.listdir(target_dir)
                if not entries:
                    return f"**{target_name}** is empty."
                # Sort: folders first, then files
                dirs = sorted([e for e in entries if os.path.isdir(os.path.join(target_dir, e))])
                files = sorted([e for e in entries if os.path.isfile(os.path.join(target_dir, e))])
                lines = []
                if dirs:
                    lines.append("**Folders:**")
                    lines.extend([f"📁 {d}" for d in dirs[:20]])
                if files:
                    lines.append("\n**Files:**")
                    lines.extend([f"📄 {f}" for f in files[:30]])
                total = len(entries)
                shown = min(50, total)
                lines.append(f"\n_{shown} of {total} items in {target_name}_")
                return "\n".join(lines)
            except PermissionError:
                return f"Access denied to {target_name}."
            except Exception as e:
                return f"Could not read folder: {e}"

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

        # ── Media ─────────────────────────────────────────────────────────────────
        elif intent == "media_play":
            # Check if user wants a specific service
            t_lower = text.lower()
            for key, url in BROWSER_APPS.items():
                if key in t_lower and key in ("spotify", "youtube"):
                    label = key.title() + (" Music" if key == "youtube" else "")
                    full_url = "https://music.youtube.com" if key == "youtube" else url
                    if self._perms:
                        perm = self._perms.needs_permission("open_browser", label, {"url": full_url, "label": label})
                        if perm.get("ask"):
                            return perm["message"]
                    return f"__OPEN_URL__{full_url}__LABEL__{label}"
            # Default: YouTube Music
            url = "https://music.youtube.com"
            if self._perms:
                perm = self._perms.needs_permission("open_browser", "YouTube Music", {"url": url, "label": "YouTube Music"})
                if perm.get("ask"):
                    return perm["message"]
            return f"__OPEN_URL__{url}__LABEL__YouTube Music"

        # ── Build App ─────────────────────────────────────────────────────────────
        elif intent == "build_app":
            if not self._executor:
                return "Executor not available."
            if not self._brain:
                return "I need the AI brain to build apps. Connect to the internet first."
            return "__BUILD__ASYNC__" + text

        elif intent == "run_code":
            if not self._executor:
                return "Executor not available."
            # Extract code block from text
            code_match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
            if code_match:
                return self._executor.run_code(code_match.group(1))
            return "Paste your code in a code block (```python ... ```) and I'll run it."

        elif intent == "self_evolve_request":
            return (
                "I can't rewrite my own neural network weights or modify my core training. "
                "No AI can do this at runtime — not ChatGPT, not Gemini, not anything available today.\n\n"
                "What I CAN actually do that gets smarter over time:\n"
                "- **Learn from web** — I crawl Wikipedia and DuckDuckGo in the background and store facts locally\n"
                "- **Retrain intent model** — say 'retrain yourself' and I update my intent detection from our conversations\n"
                "- **Build new skills** — I can write and load new Python modules that give me real new capabilities\n"
                "- **Ollama upgrade** — you can swap my brain to a bigger model anytime (llama3.1, mistral, etc)\n\n"
                "These are real. Everything else is fake."
            )

        elif intent == "self_retrain":
            if not self._trainer:
                return "Trainer not available."
            return self._trainer.retrain_intent_model()

        elif intent == "evolve_learn":
            if not self._evolution:
                return "Evolution engine not available."
            # Extract topic
            t_lower = text.lower()
            for phrase in ["learn about", "research", "study", "find out about",
                           "what do you know about", "learn more about"]:
                if phrase in t_lower:
                    topic = t_lower.split(phrase)[-1].strip().rstrip("?.")
                    if topic:
                        result = self._evolution.learn_from_web(topic)
                        return f"Learned about **{topic}**:\n\n{result[:400]}"
            # Fallback — just use brain
            return self._reason(text)

        elif intent == "evolution_stats":
            parts = []
            if self._evolution:
                parts.append(self._evolution.summary())
            if self._trainer:
                parts.append(self._trainer.summary())
            return "\n\n".join(parts) if parts else "No stats yet."

        elif intent == "list_apps":
            if self._executor:
                return self._executor.list_apps()
            return "Executor not available."

        elif intent == "stop_app":
            if self._executor:
                t_lower = text.lower()
                for w in ["stop", "kill", "close", "shut down", "app"]:
                    t_lower = t_lower.replace(w, "")
                return self._executor.stop(t_lower.strip() or "app")
            return "Executor not available."

        # ── General - Brain handles everything ───────────────────────────────────
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
        """Primary reasoning: instant local -> Groq (multi-model) -> web thinker."""
        t = text.lower().strip()

        # 0. Instant local answers - never hit Groq for these
        instant_map = {
            "who are you": f"MATCHA - your local AI OS. I run on your machine, answer questions, open apps, control your system, and build real apps.",
            "what are you": f"MATCHA - your local AI OS. I run on your machine, answer questions, open apps, control your system, and build real apps.",
            "what is matcha": "MATCHA OS - an AI operating system that runs on your machine. I answer anything, build apps, control your system, and get smarter over time.",
            "hello": f"Hey {self.user_name}. What do you need?",
            "hi": f"Hey. What do you need?",
            "hey": f"Hey. What do you need?",
            "hi matcha": f"Hey {self.user_name}. What do you need?",
            "hello matcha": f"Hey {self.user_name}. What do you need?",
            "thank you": "No problem.",
            "thanks": "No problem.",
            "ty": "No problem.",
            "what can you do": "I can: answer any question, build and run real apps/websites, open apps and websites, control your system (volume, brightness, shutdown), list files and folders, show system info, get weather and news, set reminders and notes, run and debug code, learn from the web.",
            "what do you do": "I answer questions, build apps, control your system, and get smarter the more you use me.",
            "your capabilities": "I can build apps, answer anything, control your OS, browse files, check system stats, get weather/news, set reminders, and run code.",
        }
        if t in instant_map:
            return instant_map[t]

        # 1. Local learned knowledge (free, instant)
        if self._learner and self.online:
            try:
                local_knowledge = self._learner.recall(text)
                if local_knowledge and len(local_knowledge) > 20:
                    return local_knowledge
            except Exception:
                pass

        # 2. Groq brain (cycles through 4 models on rate limit)
        if self.online and self._brain:
            try:
                answer = self._brain.think(text)
                if answer and len(answer) > 2:
                    if self._learner:
                        try:
                            self._learner.learn_and_store(
                                self._learner._extract_topic(text), answer[:500], "groq_brain"
                            )
                        except Exception:
                            pass
                    return answer
            except Exception:
                pass

        # 3. Local retriever patterns
        result = self._retriever_predict(text)
        if result:
            return result

        # 4. Web thinker fallback
        if self.online:
            try:
                thinker = self._get_thinker()
                if thinker:
                    answer = thinker.think(text)
                    if answer and len(answer) > 10:
                        if self._learner:
                            try:
                                self._learner.learn_and_store(
                                    self._learner._extract_topic(text), answer[:500], "web_thinker"
                                )
                            except Exception:
                                pass
                        return answer
            except Exception:
                pass

        return "I need an internet connection to answer that."

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

    def greet_on_boot(self) -> str:
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
