# MATCHA OS

> Your AI operating system. Built to be smarter than anything else out there.

![MATCHA OS](https://img.shields.io/badge/MATCHA%20OS-v0.4.0-4ADE80?style=flat-square&labelColor=0A0A0A)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![Groq](https://img.shields.io/badge/AI-Llama%203.3%2070B-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What is MATCHA OS?

MATCHA OS is a full AI operating system you install on top of Windows, Mac, or Linux. It runs in your browser as a full-screen black/green interface — think Jarvis, but real.

**Completely free. No subscriptions. No cloud lock-in.**

---

## Features

| Feature | Description |
|---|---|
| 🧠 **Groq AI Brain** | Llama 3.3 70B — 14,400 free requests/day |
| 🌐 **Self-Learning** | Learns from the web when online. Gets smarter every session |
| 🔒 **Permission System** | Asks before doing anything. Say "yes always" to skip next time |
| 🗣️ **Voice In/Out** | Browser Web Speech API — works on Chrome, Edge, Safari |
| 🖥️ **System Control** | Volume, brightness, launch apps, kill processes, system info |
| 🛡️ **MATCHA Shield** | Built-in antivirus and threat scanner |
| 📱 **Device Manager** | USB, Bluetooth, connected device monitoring |
| 📋 **Productivity** | Notes, reminders, clipboard history |
| 📞 **Calls** | Initiate calls with contacts |
| 🔄 **App Store** | Install apps via MATCHA Store |
| 🌍 **Weather & News** | Real-time via free APIs |
| 📺 **YouTube Search** | Find and open videos |

---

## Quick Start

### Windows

1. **Download Python 3.11+** from [python.org](https://python.org)
2. **Clone the repo:**
   ```
   git clone https://github.com/RohithMatcha25/MATCHA-OS.git
   cd MATCHA-OS
   ```
3. **Run the installer:**
   ```
   install.bat
   ```
4. **Launch:**
   ```
   launch.bat
   ```
5. Open `http://localhost:8080` in Chrome or Edge

### Linux / Mac

```bash
git clone https://github.com/RohithMatcha25/MATCHA-OS.git
cd MATCHA-OS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Open `http://localhost:8080` in your browser.

---

## How It Works

```
User speaks/types
       ↓
Intent Detection (local, instant)
       ↓
┌──────────────────────────────┐
│  Permission Check            │ ← asks you first for system actions
│  "Open YouTube? (yes/no)"    │
└──────────────────────────────┘
       ↓ yes
┌──────────────────────────────┐
│  Route to handler:           │
│  • Groq Brain (AI chat)      │
│  • System Control (OS cmds)  │
│  • Web Agent (weather/news)  │
│  • Self-Learner (memory)     │
└──────────────────────────────┘
       ↓
Response → Self-Learning stores answer
       ↓
User sees response
```

---

## Self-Learning

When connected to the internet, MATCHA learns from every interaction:

- Stores facts from Wikipedia, DuckDuckGo, and web searches locally
- Topics you ask about 3+ times → MATCHA goes deeper and learns everything about them
- Next time you ask → answers from local memory (instant, no API call)
- Check what MATCHA has learned: *"What have you learned?"*

---

## Permission System

MATCHA asks before doing anything that affects your system:

| Action | Behaviour |
|---|---|
| Open website | Asks once. Say "yes always" to skip forever |
| Launch app | Asks once. Say "yes always" to skip forever |
| Install software | Always asks |
| Shutdown / Restart | Always asks. Cannot be "always allowed" |
| Kill process | Always asks. Cannot be "always allowed" |

---

## Tech Stack

- **Backend:** Python 3.11 + Flask
- **AI Brain:** Groq API (Llama 3.3 70B) — free tier
- **Frontend:** Pure HTML/CSS/JS — no frameworks
- **Voice:** Web Speech API (browser-native)
- **Database:** SQLite (local, nothing leaves your machine)
- **Web Intel:** Wikipedia REST API + DuckDuckGo Instant Answers
- **Security:** MATCHA Shield (local heuristic scanner)

---

## Project Structure

```
matcha-os/
├── main.py                    # Flask server
├── core/
│   ├── matcha_ai.py           # Core AI — intent + routing
│   ├── brain/
│   │   └── matcha_brain.py    # Groq + Llama 3.3 70B
│   ├── learning/
│   │   └── self_learner.py    # Self-learning engine
│   ├── permissions/
│   │   └── permission_manager.py  # Permission system
│   ├── system/
│   │   └── system_control.py  # OS control (Windows/Linux/Mac)
│   ├── online/
│   │   ├── web_agent.py       # Weather, news, YouTube, Wikipedia
│   │   └── thinker.py         # Web reasoning engine
│   ├── security/
│   │   └── matcha_shield.py   # Antivirus / threat scanner
│   ├── devices/
│   │   └── device_manager.py  # USB + Bluetooth
│   ├── productivity/
│   │   └── matcha_productivity.py  # Notes + reminders
│   ├── calls/
│   │   └── matcha_calls.py    # Calling
│   ├── store/
│   │   └── matcha_store.py    # App store
│   └── model/
│       └── weights/
│           └── matcha_model.json  # 207 trained examples
├── interface/
│   └── index.html             # Full-screen UI
├── dist/
│   └── patch.py               # Auto-updater
└── requirements.txt
```

---

## Roadmap

- [ ] Persistent memory across sessions (long-term user profile)
- [ ] Camera / image understanding
- [ ] Code editor + one-click deploy
- [ ] Encrypted vault (passwords, secrets)
- [ ] Android companion widget
- [ ] Smart home control (Home Assistant integration)
- [ ] Email integration
- [ ] Expense tracker

---

## Contributing

This is an active project. PRs welcome.

1. Fork it
2. Create your branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a PR

---

## License

MIT — free to use, modify, and distribute.

---

Built by [Rohith Matcha](https://github.com/RohithMatcha25)
