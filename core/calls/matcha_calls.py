"""
MATCHA Calls — Voice & Video calling
Built-in calling — no Zoom, no Teams needed.
Uses WebRTC for peer-to-peer calls.
"""

import subprocess
import platform
import json
import uuid
from datetime import datetime
from pathlib import Path

PLATFORM = platform.system()
CALL_LOG = Path.home() / ".matcha" / "call_log.json"


class MatchaCalls:
    def __init__(self, alert_callback=None):
        self.active_call = None
        self.alert_callback = alert_callback
        self.contacts = self._load_contacts()
        CALL_LOG.parent.mkdir(parents=True, exist_ok=True)

    def _load_contacts(self) -> dict:
        path = Path.home() / ".matcha" / "contacts.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_contacts(self):
        path = Path.home() / ".matcha" / "contacts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.contacts, f, indent=2)

    def add_contact(self, name: str, identifier: str) -> str:
        """Add a contact (email or phone)."""
        self.contacts[name.lower()] = {
            "name": name,
            "identifier": identifier,
            "added": datetime.now().isoformat()
        }
        self._save_contacts()
        return f"{name} added to contacts."

    def find_contact(self, query: str) -> dict:
        query = query.lower().strip()
        # Exact match
        if query in self.contacts:
            return self.contacts[query]
        # Fuzzy match
        for key, contact in self.contacts.items():
            if query in key or query in contact.get("name", "").lower():
                return contact
        return None

    def initiate_call(self, contact_name: str, video: bool = False) -> str:
        """Initiate a call to a contact."""
        contact = self.find_contact(contact_name)

        if not contact:
            return (f"I don't have {contact_name} in your contacts. "
                    f"Say 'Add {contact_name} with number/email [contact]' to add them.")

        call_type = "video" if video else "voice"
        call_id = str(uuid.uuid4())[:8]

        self.active_call = {
            "id": call_id,
            "contact": contact["name"],
            "type": call_type,
            "started": datetime.now().isoformat(),
            "status": "calling"
        }

        # Log the call
        self._log_call(contact["name"], call_type, "outgoing")

        # Try to open a video call via browser (Jitsi — free, no account needed)
        if video:
            room_name = f"matcha-{contact_name.lower().replace(' ', '-')}-{call_id}"
            call_url = f"https://meet.jit.si/{room_name}"
            try:
                if PLATFORM == "Linux":
                    subprocess.Popen(["xdg-open", call_url])
                elif PLATFORM == "Darwin":
                    subprocess.Popen(["open", call_url])
                elif PLATFORM == "Windows":
                    subprocess.Popen(["start", call_url], shell=True)
                return (f"Starting video call with {contact['name']}. "
                        f"Opening Jitsi Meet. Share this link with them: {call_url}")
            except:
                return f"Video call ready. Share this link with {contact['name']}: {call_url}"

        return f"Calling {contact['name']}. Voice calling coming in next update."

    def end_call(self) -> str:
        if self.active_call:
            name = self.active_call["contact"]
            self.active_call = None
            return f"Call with {name} ended."
        return "No active call."

    def list_contacts(self) -> str:
        if not self.contacts:
            return "No contacts saved. Add someone with 'Add [name] with number [number]'."
        lines = [f"• {v['name']} — {v['identifier']}" for v in self.contacts.values()]
        return "Contacts:\n" + "\n".join(lines)

    def _log_call(self, contact: str, call_type: str, direction: str):
        try:
            log = []
            if CALL_LOG.exists():
                with open(CALL_LOG) as f:
                    log = json.load(f)
            log.append({
                "timestamp": datetime.now().isoformat(),
                "contact": contact,
                "type": call_type,
                "direction": direction
            })
            with open(CALL_LOG, "w") as f:
                json.dump(log[-100:], f, indent=2)  # Keep last 100
        except:
            pass

    def get_call_history(self) -> str:
        if not CALL_LOG.exists():
            return "No call history."
        with open(CALL_LOG) as f:
            log = json.load(f)
        if not log:
            return "No call history."
        recent = log[-5:][::-1]
        lines = []
        for call in recent:
            dt = call["timestamp"][:16].replace("T", " ")
            lines.append(f"• {call['contact']} — {call['type']} call ({call['direction']}) at {dt}")
        return "Recent calls:\n" + "\n".join(lines)
