"""
MATCHA Persistent Memory
Remembers everything across sessions. Stores locally. Never leaves the machine.
"""

import os, json, sqlite3, pathlib
from datetime import datetime
from typing import Optional, List

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MEMORY_DB = os.path.join(BASE, "core", "memory", "persistent.db")


class MatchaMemoryPersistent:
    def __init__(self):
        pathlib.Path(os.path.dirname(MEMORY_DB)).mkdir(parents=True, exist_ok=True)
        self._init_db()
        print("[MATCHA Memory] Persistent memory loaded.")

    def _init_db(self):
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                category TEXT,
                key TEXT,
                value TEXT,
                ts TEXT,
                UNIQUE(category, key)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                role TEXT,
                content TEXT,
                ts TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY,
                fact TEXT,
                source TEXT,
                ts TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                ts TEXT
            )""")

    # ── Remember/Recall ───────────────────────────────────────────────────────

    def remember(self, category: str, key: str, value: str) -> str:
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute(
                "INSERT OR REPLACE INTO memories (category, key, value, ts) VALUES (?, ?, ?, ?)",
                (category, key, value, datetime.now().isoformat())
            )
        return f"Remembered: {key} = {value}"

    def recall(self, key: str) -> Optional[str]:
        with sqlite3.connect(MEMORY_DB) as c:
            row = c.execute(
                "SELECT value FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY ts DESC LIMIT 1",
                (f"%{key}%", f"%{key}%")
            ).fetchone()
        return row[0] if row else None

    def recall_all(self, category: str = None) -> List[dict]:
        with sqlite3.connect(MEMORY_DB) as c:
            if category:
                rows = c.execute(
                    "SELECT category, key, value, ts FROM memories WHERE category=? ORDER BY ts DESC",
                    (category,)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT category, key, value, ts FROM memories ORDER BY ts DESC LIMIT 50"
                ).fetchall()
        return [{"category": r[0], "key": r[1], "value": r[2], "ts": r[3]} for r in rows]

    def forget(self, key: str) -> str:
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute("DELETE FROM memories WHERE key LIKE ?", (f"%{key}%",))
        return f"Forgotten: {key}"

    # ── Conversation History ──────────────────────────────────────────────────

    def log_conversation(self, role: str, content: str):
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute(
                "INSERT INTO conversations (role, content, ts) VALUES (?, ?, ?)",
                (role, content, datetime.now().isoformat())
            )
            # Keep last 1000 messages
            c.execute(
                "DELETE FROM conversations WHERE id NOT IN (SELECT id FROM conversations ORDER BY id DESC LIMIT 1000)"
            )

    def get_recent_conversations(self, limit: int = 20) -> List[dict]:
        with sqlite3.connect(MEMORY_DB) as c:
            rows = c.execute(
                "SELECT role, content, ts FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [{"role": r[0], "content": r[1], "ts": r[2]} for r in reversed(rows)]

    def get_conversation_context(self, limit: int = 6) -> str:
        """Get recent conversation as context string for the brain."""
        recent = self.get_recent_conversations(limit)
        if not recent:
            return ""
        lines = []
        for m in recent:
            lines.append(f"{m['role'].upper()}: {m['content'][:200]}")
        return "\n".join(lines)

    # ── Facts ─────────────────────────────────────────────────────────────────

    def store_fact(self, fact: str, source: str = "user"):
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute(
                "INSERT INTO facts (fact, source, ts) VALUES (?, ?, ?)",
                (fact, source, datetime.now().isoformat())
            )

    def search_facts(self, query: str) -> List[str]:
        with sqlite3.connect(MEMORY_DB) as c:
            rows = c.execute(
                "SELECT fact FROM facts WHERE fact LIKE ? ORDER BY ts DESC LIMIT 5",
                (f"%{query}%",)
            ).fetchall()
        return [r[0] for r in rows]

    # ── Preferences ──────────────────────────────────────────────────────────

    def set_preference(self, key: str, value: str):
        with sqlite3.connect(MEMORY_DB) as c:
            c.execute(
                "INSERT OR REPLACE INTO preferences (key, value, ts) VALUES (?, ?, ?)",
                (key, value, datetime.now().isoformat())
            )

    def get_preference(self, key: str) -> Optional[str]:
        with sqlite3.connect(MEMORY_DB) as c:
            row = c.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> str:
        with sqlite3.connect(MEMORY_DB) as c:
            memories = c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
            conversations = c.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            facts = c.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        return f"Memory: {memories} stored memories, {conversations} conversation messages, {facts} facts."

    def format_memories(self) -> str:
        all_mem = self.recall_all()
        if not all_mem:
            return "Nothing stored yet."
        lines = []
        by_cat = {}
        for m in all_mem:
            by_cat.setdefault(m["category"], []).append(f"  • {m['key']}: {m['value']}")
        for cat, items in by_cat.items():
            lines.append(f"**{cat.title()}:**")
            lines.extend(items[:10])
        return "\n".join(lines)
