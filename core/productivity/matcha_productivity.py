"""
MATCHA Reminders & Notes
Built-in productivity — reminders, notes, clipboard manager.
All local, all private.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
import re

REMINDERS_FILE = Path.home() / ".matcha" / "reminders.json"
NOTES_FILE = Path.home() / ".matcha" / "notes.json"
CLIPBOARD_FILE = Path.home() / ".matcha" / "clipboard.json"


class MatchaProductivity:
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback or self._default_alert
        self.reminders = self._load_reminders()
        self.notes = self._load_notes()
        self.clipboard = self._load_clipboard()
        # Start reminder checker
        self._checker_thread = threading.Thread(target=self._check_reminders, daemon=True)
        self._checker_thread.start()

    # ── Reminders ──

    def add_reminder(self, text: str, when_str: str) -> str:
        """Parse natural language time and set reminder."""
        due_time = self._parse_time(when_str)
        if not due_time:
            return f"I couldn't understand '{when_str}'. Try '10 minutes', '3pm', 'tomorrow 9am'."

        reminder = {
            "id": len(self.reminders) + 1,
            "text": text,
            "due": due_time.isoformat(),
            "created": datetime.now().isoformat(),
            "fired": False
        }
        self.reminders.append(reminder)
        self._save_reminders()

        time_str = due_time.strftime("%H:%M on %d %b")
        return f"Reminder set: '{text}' at {time_str}."

    def list_reminders(self) -> str:
        active = [r for r in self.reminders if not r["fired"]]
        if not active:
            return "No active reminders."
        lines = []
        for r in active:
            due = datetime.fromisoformat(r["due"]).strftime("%H:%M, %d %b")
            lines.append(f"• [{r['id']}] {r['text']} — due {due}")
        return "Reminders:\n" + "\n".join(lines)

    def delete_reminder(self, reminder_id: int) -> str:
        for r in self.reminders:
            if r["id"] == reminder_id:
                self.reminders.remove(r)
                self._save_reminders()
                return f"Reminder '{r['text']}' deleted."
        return f"Reminder {reminder_id} not found."

    def _check_reminders(self):
        """Background thread — fires reminders when due."""
        while True:
            now = datetime.now()
            for r in self.reminders:
                if not r["fired"]:
                    due = datetime.fromisoformat(r["due"])
                    if now >= due:
                        r["fired"] = True
                        self._save_reminders()
                        self.alert_callback("reminder", r["text"])
            time.sleep(30)  # Check every 30 seconds

    def _parse_time(self, text: str) -> datetime:
        """Parse natural language time expressions."""
        text = text.lower().strip()
        now = datetime.now()

        # "in X minutes/hours"
        m = re.search(r'in (\d+) (minute|hour|second)s?', text)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            if unit == "second":
                return now + timedelta(seconds=amount)
            elif unit == "minute":
                return now + timedelta(minutes=amount)
            elif unit == "hour":
                return now + timedelta(hours=amount)

        # "at Xpm / X:XX"
        m = re.search(r'at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            ampm = m.group(3)
            if ampm == "pm" and hour < 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if due <= now:
                due += timedelta(days=1)
            return due

        # "tomorrow"
        if "tomorrow" in text:
            base = now + timedelta(days=1)
            m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text)
            if m:
                hour = int(m.group(1))
                minute = int(m.group(2)) if m.group(2) else 0
                ampm = m.group(3)
                if ampm == "pm" and hour < 12:
                    hour += 12
                return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return base.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    def _load_reminders(self) -> list:
        if REMINDERS_FILE.exists():
            with open(REMINDERS_FILE) as f:
                return json.load(f)
        return []

    def _save_reminders(self):
        REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(REMINDERS_FILE, "w") as f:
            json.dump(self.reminders, f, indent=2)

    # ── Notes ──

    def add_note(self, title: str, content: str) -> str:
        note = {
            "id": len(self.notes) + 1,
            "title": title,
            "content": content,
            "created": datetime.now().isoformat()
        }
        self.notes.append(note)
        self._save_notes()
        return f"Note saved: '{title}'."

    def list_notes(self) -> str:
        if not self.notes:
            return "No notes saved."
        lines = [f"• [{n['id']}] {n['title']} — {n['created'][:10]}" for n in self.notes[-10:]]
        return "Notes:\n" + "\n".join(lines)

    def read_note(self, query: str) -> str:
        query = query.lower()
        for note in self.notes:
            if query in note["title"].lower() or str(note["id"]) == query:
                return f"{note['title']}:\n{note['content']}"
        return f"Note '{query}' not found."

    def delete_note(self, note_id: int) -> str:
        for n in self.notes:
            if n["id"] == note_id:
                self.notes.remove(n)
                self._save_notes()
                return f"Note '{n['title']}' deleted."
        return f"Note {note_id} not found."

    def _load_notes(self) -> list:
        if NOTES_FILE.exists():
            with open(NOTES_FILE) as f:
                return json.load(f)
        return []

    def _save_notes(self):
        NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(NOTES_FILE, "w") as f:
            json.dump(self.notes, f, indent=2)

    # ── Clipboard Manager ──

    def save_clipboard(self, content: str) -> str:
        self.clipboard.insert(0, {
            "content": content,
            "saved": datetime.now().isoformat()
        })
        self.clipboard = self.clipboard[:50]  # Keep last 50
        self._save_clipboard_file()
        return "Saved to clipboard history."

    def list_clipboard(self) -> str:
        if not self.clipboard:
            return "Clipboard history is empty."
        lines = [f"• [{i+1}] {c['content'][:60]}..." if len(c['content']) > 60
                 else f"• [{i+1}] {c['content']}"
                 for i, c in enumerate(self.clipboard[:10])]
        return "Clipboard history:\n" + "\n".join(lines)

    def _load_clipboard(self) -> list:
        if CLIPBOARD_FILE.exists():
            with open(CLIPBOARD_FILE) as f:
                return json.load(f)
        return []

    def _save_clipboard_file(self):
        CLIPBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CLIPBOARD_FILE, "w") as f:
            json.dump(self.clipboard, f, indent=2)

    def _default_alert(self, alert_type: str, message: str):
        print(f"[MATCHA Reminder] ⏰ {message}")
