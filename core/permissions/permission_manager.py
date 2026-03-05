"""
MATCHA Permission Manager
Intercepts actions that affect the user's system and asks for confirmation.
Remembers "always allow" choices so it doesn't ask repeatedly.
"""

import sqlite3
import json
import datetime
from pathlib import Path

PERMS_DB = Path(__file__).parent.parent / "memory" / "permissions.db"

# Actions that ALWAYS need permission (no "always allow")
ALWAYS_ASK = {"shutdown", "restart", "kill_process", "delete_file"}

# Actions that CAN be "always allowed"
CAN_REMEMBER = {"open_browser", "open_app", "install_app", "send_call"}


class PermissionManager:
    """
    Asks the user before MATCHA does anything that affects the system.
    
    Flow:
    1. MATCHA wants to do something (e.g. open Chrome)
    2. PermissionManager checks: has user said "always allow" for this?
       - Yes → proceed silently
       - No  → return a confirmation request to the UI
    3. User says "yes" / "go ahead" / "do it" → action executes
    4. User can say "always allow opening apps" → remembered forever
    """

    PENDING_ACTIONS = {}  # session-level pending confirmations

    def __init__(self):
        PERMS_DB.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(PERMS_DB), check_same_thread=False)
        self._init_db()
        print("[MATCHA Perms] Permission manager ready.")

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS always_allow (
                action_type TEXT PRIMARY KEY,
                granted_at TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS permission_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                description TEXT,
                decision TEXT,
                decided_at TEXT
            )
        """)
        self.conn.commit()

    def needs_permission(self, action_type: str, description: str, action_data: dict) -> dict:
        """
        Check if this action needs user permission.
        
        Returns:
          {"proceed": True}  — execute immediately
          {"ask": True, "message": "...", "token": "..."}  — ask user first
        """
        # Always-ask actions — never skip
        if action_type in ALWAYS_ASK:
            token = self._store_pending(action_type, description, action_data)
            return {
                "ask": True,
                "message": self._format_ask(action_type, description),
                "token": token,
                "can_remember": False,
            }

        # Check if user has said "always allow" for this type
        if self._is_always_allowed(action_type):
            return {"proceed": True}

        # Ask for permission
        token = self._store_pending(action_type, description, action_data)
        can_remember = action_type in CAN_REMEMBER
        return {
            "ask": True,
            "message": self._format_ask(action_type, description),
            "token": token,
            "can_remember": can_remember,
        }

    def confirm(self, token: str, always: bool = False) -> dict:
        """
        User said yes. Execute the stored action.
        Returns {"proceed": True, "action_data": {...}}
        """
        pending = PermissionManager.PENDING_ACTIONS.get(token)
        if not pending:
            return {"proceed": False, "error": "No pending action found."}

        action_type = pending["action_type"]
        action_data = pending["action_data"]

        # Log decision
        self._log(action_type, pending["description"], "granted")

        # Remember "always allow" if requested
        if always and action_type in CAN_REMEMBER:
            self._set_always_allow(action_type)

        # Clean up
        del PermissionManager.PENDING_ACTIONS[token]

        return {"proceed": True, "action_type": action_type, "action_data": action_data}

    def deny(self, token: str) -> bool:
        """User said no."""
        pending = PermissionManager.PENDING_ACTIONS.get(token)
        if pending:
            self._log(pending["action_type"], pending["description"], "denied")
            del PermissionManager.PENDING_ACTIONS[token]
        return True

    def is_confirmation(self, text: str) -> tuple:
        """
        Check if user's message is a yes/no to a pending action.
        Returns (is_confirm: bool, is_yes: bool, always: bool)
        """
        t = text.lower().strip()
        yes_words = ["yes", "yeah", "yep", "sure", "ok", "okay", "go ahead", "do it",
                     "proceed", "confirm", "yup", "absolutely", "definitely", "open it",
                     "launch it", "run it", "allow"]
        no_words = ["no", "nope", "cancel", "stop", "don't", "abort", "deny", "refuse"]
        always_words = ["always", "every time", "remember", "don't ask again", "always allow"]

        has_always = any(w in t for w in always_words)

        if any(t == w or t.startswith(w) for w in yes_words):
            return True, True, has_always
        if any(t == w or t.startswith(w) for w in no_words):
            return True, False, False

        return False, False, False

    def get_pending(self) -> dict:
        """Get the most recent pending action token."""
        if PermissionManager.PENDING_ACTIONS:
            # Return the last pending action
            token = list(PermissionManager.PENDING_ACTIONS.keys())[-1]
            return {"token": token, **PermissionManager.PENDING_ACTIONS[token]}
        return {}

    def revoke_always_allow(self, action_type: str):
        """Remove an always-allow setting."""
        self.conn.execute("DELETE FROM always_allow WHERE action_type = ?", (action_type,))
        self.conn.commit()

    def get_always_allowed(self) -> list:
        """List all always-allowed action types."""
        cursor = self.conn.execute("SELECT action_type, granted_at FROM always_allow")
        return cursor.fetchall()

    # ── Private ──

    def _store_pending(self, action_type: str, description: str, action_data: dict) -> str:
        """Store action waiting for confirmation. Returns token."""
        import uuid
        token = str(uuid.uuid4())[:8]
        PermissionManager.PENDING_ACTIONS[token] = {
            "action_type": action_type,
            "description": description,
            "action_data": action_data,
            "created_at": datetime.datetime.now().isoformat(),
        }
        return token

    def _format_ask(self, action_type: str, description: str) -> str:
        """Format the confirmation question."""
        msgs = {
            "open_browser": f"Open {description} in your browser?",
            "open_app": f"Launch {description}?",
            "install_app": f"Install {description}?",
            "send_call": f"Call {description}?",
            "shutdown": f"Shut down your computer?",
            "restart": f"Restart your computer?",
            "kill_process": f"Terminate {description}?",
            "delete_file": f"Delete {description}?",
        }
        return msgs.get(action_type, f"Do this: {description}?") + " (yes / no)"

    def _is_always_allowed(self, action_type: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM always_allow WHERE action_type = ?", (action_type,)
        )
        return cursor.fetchone() is not None

    def _set_always_allow(self, action_type: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO always_allow (action_type, granted_at) VALUES (?, ?)",
            (action_type, datetime.datetime.now().isoformat())
        )
        self.conn.commit()

    def _log(self, action_type: str, description: str, decision: str):
        self.conn.execute(
            "INSERT INTO permission_log (action_type, description, decision, decided_at) VALUES (?, ?, ?, ?)",
            (action_type, description, decision, datetime.datetime.now().isoformat())
        )
        self.conn.commit()
