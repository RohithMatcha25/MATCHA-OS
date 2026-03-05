"""
MATCHA Evolution Engine
Crawls the internet for new knowledge and skills.
Runs in background threads — MATCHA gets smarter while you use it.
"""

import os, sqlite3, json, time, threading, pathlib, re
from datetime import datetime
from typing import Optional

BASE = os.path.join(os.path.dirname(__file__), "..", "..")
EVOLUTION_DB = os.path.join(BASE, "core", "memory", "evolution.db")
SKILLS_DIR = os.path.join(BASE, "core", "skills")


class MatchaEvolution:
    def __init__(self):
        pathlib.Path(os.path.dirname(EVOLUTION_DB)).mkdir(parents=True, exist_ok=True)
        pathlib.Path(SKILLS_DIR).mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._crawl_thread = None
        self._running = False
        print("[MATCHA Evolution] Evolution engine ready.")

    def _init_db(self):
        with sqlite3.connect(EVOLUTION_DB) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS learned (
                id INTEGER PRIMARY KEY,
                topic TEXT,
                content TEXT,
                source TEXT,
                ts TEXT,
                used_count INTEGER DEFAULT 0
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                code TEXT,
                description TEXT,
                ts TEXT,
                active INTEGER DEFAULT 1
            )""")

    # ── Internet Learning ─────────────────────────────────────────────────────

    def learn_from_web(self, topic: str) -> str:
        """Fetch real knowledge about a topic from multiple sources."""
        facts = []

        # Source 1: Wikipedia REST API
        try:
            import urllib.request, json as _json
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ','_')}"
            req = urllib.request.Request(url, headers={"User-Agent": "MATCHA-OS/0.4"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = _json.loads(r.read())
                extract = data.get("extract", "")
                if extract and len(extract) > 50:
                    facts.append(("wikipedia", extract[:800]))
        except Exception:
            pass

        # Source 2: DuckDuckGo Instant Answer
        try:
            import urllib.request, urllib.parse, json as _json
            q = urllib.parse.quote(topic)
            url = f"https://api.duckduckgo.com/?q={q}&format=json&no_redirect=1&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "MATCHA-OS/0.4"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = _json.loads(r.read())
                abstract = data.get("AbstractText", "")
                if abstract and len(abstract) > 30:
                    facts.append(("duckduckgo", abstract[:500]))
        except Exception:
            pass

        if not facts:
            return f"Could not find information on '{topic}' right now."

        # Store all facts
        combined = " | ".join([f[1] for f in facts])
        with sqlite3.connect(EVOLUTION_DB) as c:
            existing = c.execute(
                "SELECT id FROM learned WHERE topic=?", (topic.lower(),)
            ).fetchone()
            if existing:
                c.execute(
                    "UPDATE learned SET content=?, ts=? WHERE topic=?",
                    (combined, datetime.now().isoformat(), topic.lower())
                )
            else:
                c.execute(
                    "INSERT INTO learned (topic, content, source, ts) VALUES (?, ?, ?, ?)",
                    (topic.lower(), combined, ",".join([f[0] for f in facts]), datetime.now().isoformat())
                )

        return combined[:500]

    def recall(self, topic: str) -> Optional[str]:
        """Recall stored knowledge about a topic."""
        with sqlite3.connect(EVOLUTION_DB) as c:
            row = c.execute(
                "SELECT content FROM learned WHERE topic LIKE ? ORDER BY used_count DESC LIMIT 1",
                (f"%{topic.lower()}%",)
            ).fetchone()
            if row:
                c.execute("UPDATE learned SET used_count = used_count + 1 WHERE topic LIKE ?",
                          (f"%{topic.lower()}%",))
                return row[0]
        return None

    def start_background_crawl(self, topics: list):
        """Start a background thread crawling a list of topics."""
        def crawl():
            self._running = True
            for topic in topics:
                if not self._running:
                    break
                try:
                    self.learn_from_web(topic)
                    time.sleep(2)
                except Exception:
                    pass
            self._running = False

        self._crawl_thread = threading.Thread(target=crawl, daemon=True)
        self._crawl_thread.start()
        return f"Background learning started on {len(topics)} topics."

    # ── Runtime Skill Loading ─────────────────────────────────────────────────

    def add_skill(self, name: str, code: str, description: str) -> str:
        """
        Add a new Python skill to MATCHA at runtime.
        The code is saved and imported — MATCHA literally gains a new capability.
        """
        skill_file = os.path.join(SKILLS_DIR, f"{name}.py")
        try:
            # Validate syntax
            import ast
            ast.parse(code)
        except SyntaxError as e:
            return f"Skill has syntax error: {e}"

        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(code)

        with sqlite3.connect(EVOLUTION_DB) as c:
            c.execute("""INSERT OR REPLACE INTO skills (name, code, description, ts, active)
                         VALUES (?, ?, ?, ?, 1)""",
                      (name, code, description, datetime.now().isoformat()))

        # Load it immediately
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(f"matcha_skill_{name}", skill_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return f"✅ New skill '{name}' loaded. MATCHA can now: {description}"
        except Exception as e:
            return f"Skill saved but failed to load: {e}"

    def list_skills(self) -> str:
        with sqlite3.connect(EVOLUTION_DB) as c:
            rows = c.execute(
                "SELECT name, description FROM skills WHERE active=1"
            ).fetchall()
        if not rows:
            return "No custom skills loaded yet."
        return "\n".join([f"• **{r[0]}**: {r[1]}" for r in rows])

    def get_stats(self) -> dict:
        with sqlite3.connect(EVOLUTION_DB) as c:
            facts = c.execute("SELECT COUNT(*) FROM learned").fetchone()[0]
            top = c.execute(
                "SELECT topic, used_count FROM learned ORDER BY used_count DESC LIMIT 5"
            ).fetchall()
            skills = c.execute("SELECT COUNT(*) FROM skills WHERE active=1").fetchone()[0]
        return {"facts_learned": facts, "top_topics": top, "custom_skills": skills}

    def summary(self) -> str:
        s = self.get_stats()
        top = ", ".join([f"{t[0]} ({t[1]}x)" for t in s["top_topics"]])
        return (
            f"I've learned {s['facts_learned']} facts from the internet. "
            f"Most studied: {top or 'nothing yet'}. "
            f"Custom skills loaded: {s['custom_skills']}."
        )
