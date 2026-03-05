"""
MATCHA Self-Learning Engine
Learns from the web when online. Stores knowledge locally. Gets smarter over time.
"""

import sqlite3
import json
import re
import datetime
import requests
import urllib.parse
from pathlib import Path
from typing import Optional

KNOWLEDGE_DB = Path(__file__).parent.parent / "memory" / "knowledge.db"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 6


class SelfLearner:
    """
    MATCHA's self-learning engine.
    - Learns facts from Wikipedia, DDG, and web when online
    - Stores everything locally in a knowledge DB
    - Recalls learned knowledge on future queries
    - Tracks what topics the user cares about and deepens knowledge there
    """

    def __init__(self):
        KNOWLEDGE_DB.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(KNOWLEDGE_DB), check_same_thread=False)
        self._init_db()
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        print("[MATCHA Learner] Self-learning engine ready.")

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                learned_at TEXT,
                query_count INTEGER DEFAULT 0,
                UNIQUE(topic, fact)
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS topic_interest (
                topic TEXT PRIMARY KEY,
                count INTEGER DEFAULT 1,
                last_asked TEXT,
                deepened INTEGER DEFAULT 0
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_topic ON knowledge(topic)
        """)
        self.conn.commit()

    def learn_from_query(self, query: str) -> Optional[str]:
        """
        When user asks something: check local knowledge first,
        if not found learn it from the web and store it.
        Returns the answer if found/learned, None otherwise.
        """
        topic = self._extract_topic(query)
        if not topic or len(topic) < 3:
            return None

        # Track interest
        self._track_interest(topic)

        # Check local knowledge first
        local = self._recall(topic, query)
        if local:
            self._increment_query_count(topic)
            return local

        # Not known — learn it from the web
        learned = self._learn_from_web(topic, query)
        if learned:
            self._store(topic, learned, source="web")
            return learned

        return None

    def recall(self, query: str) -> Optional[str]:
        """Just check local knowledge — no web call."""
        topic = self._extract_topic(query)
        if not topic:
            return None
        return self._recall(topic, query)

    def learn_and_store(self, topic: str, fact: str, source: str = "web"):
        """Directly store a piece of knowledge."""
        self._store(topic, fact, source)

    def get_top_interests(self, limit: int = 10) -> list:
        """What topics does the user care most about?"""
        cursor = self.conn.execute(
            "SELECT topic, count FROM topic_interest ORDER BY count DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()

    def deepen_knowledge(self, topic: str) -> int:
        """
        Go deeper on a topic — fetch more detailed info.
        Called when user has asked about a topic 3+ times.
        Returns number of new facts learned.
        """
        # Check if already deepened
        cursor = self.conn.execute(
            "SELECT deepened FROM topic_interest WHERE topic = ?", (topic,)
        )
        row = cursor.fetchone()
        if row and row[0]:
            return 0  # Already deepened

        # Fetch more detailed knowledge
        facts_learned = 0
        try:
            # Wikipedia full intro
            url = (
                "https://en.wikipedia.org/w/api.php?action=query&prop=extracts"
                "&exintro=true&explaintext=true&titles=" + urllib.parse.quote(topic)
                + "&format=json&utf8=1"
            )
            r = self.session.get(url, timeout=TIMEOUT)
            pages = r.json().get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            extract = page.get("extract", "")
            if extract:
                # Split into paragraphs and store each as a separate fact
                paragraphs = [p.strip() for p in extract.split("\n\n") if len(p.strip()) > 50]
                for para in paragraphs[:5]:
                    self._store(topic, para, source="wikipedia_deep")
                    facts_learned += 1

            # Mark as deepened
            self.conn.execute(
                "UPDATE topic_interest SET deepened = 1 WHERE topic = ?", (topic,)
            )
            self.conn.commit()
        except Exception:
            pass

        return facts_learned

    # ── Private methods ──

    def _extract_topic(self, query: str) -> str:
        """Extract the main topic from a query."""
        q = query.lower().strip()
        # Remove common question words
        q = re.sub(r'^(what is|what are|who is|who was|tell me about|explain|define|how does|where is|when was|why is|what does)\s+', '', q, flags=re.I)
        q = re.sub(r'\?+$', '', q).strip()
        # Take first 4 words max as topic
        words = q.split()[:4]
        return " ".join(words).strip()

    def _recall(self, topic: str, query: str) -> Optional[str]:
        """Search local knowledge for relevant info."""
        try:
            # Exact topic match first
            cursor = self.conn.execute(
                "SELECT fact FROM knowledge WHERE topic = ? ORDER BY query_count DESC LIMIT 3",
                (topic,)
            )
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

            # Partial topic match
            cursor = self.conn.execute(
                "SELECT fact FROM knowledge WHERE topic LIKE ? ORDER BY query_count DESC LIMIT 3",
                (f"%{topic}%",)
            )
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

        except Exception:
            pass
        return None

    def _learn_from_web(self, topic: str, query: str) -> Optional[str]:
        """Fetch knowledge from web sources."""
        # 1. Wikipedia
        try:
            search_url = (
                "https://en.wikipedia.org/w/api.php?action=query&list=search"
                "&srsearch=" + urllib.parse.quote(topic)
                + "&srlimit=1&format=json"
            )
            r = self.session.get(search_url, timeout=TIMEOUT)
            results = r.json().get("query", {}).get("search", [])
            if results:
                title = results[0]["title"]
                summary_url = (
                    "https://en.wikipedia.org/api/rest_v1/page/summary/"
                    + urllib.parse.quote(title.replace(" ", "_"))
                )
                r2 = self.session.get(summary_url, timeout=TIMEOUT)
                extract = r2.json().get("extract", "")
                if extract and len(extract) > 30:
                    # Take first 2 sentences
                    sentences = re.split(r'(?<=[.!?])\s+', extract)
                    answer = " ".join(sentences[:2])
                    return answer
        except Exception:
            pass

        # 2. DDG Instant Answer
        try:
            url = (
                "https://api.duckduckgo.com/?q=" + urllib.parse.quote(query)
                + "&format=json&no_html=1&skip_disambig=1"
            )
            r = self.session.get(url, timeout=TIMEOUT)
            d = r.json()
            abstract = d.get("AbstractText", "").strip()
            if abstract and len(abstract) > 30:
                return abstract
            answer = d.get("Answer", "").strip()
            if answer:
                return answer
        except Exception:
            pass

        return None

    def _store(self, topic: str, fact: str, source: str = "web"):
        """Store a fact in the knowledge DB."""
        try:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO knowledge (topic, fact, source, learned_at, query_count)
                VALUES (?, ?, ?, ?, 0)
                """,
                (topic.lower(), fact, source, datetime.datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception:
            pass

    def _track_interest(self, topic: str):
        """Track what topics the user asks about."""
        try:
            self.conn.execute(
                """
                INSERT INTO topic_interest (topic, count, last_asked) VALUES (?, 1, ?)
                ON CONFLICT(topic) DO UPDATE SET count = count + 1, last_asked = ?
                """,
                (topic.lower(), datetime.datetime.now().isoformat(),
                 datetime.datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception:
            pass

    def _increment_query_count(self, topic: str):
        try:
            self.conn.execute(
                "UPDATE knowledge SET query_count = query_count + 1 WHERE topic = ?",
                (topic.lower(),)
            )
            self.conn.commit()
        except Exception:
            pass

    def get_stats(self) -> dict:
        """How much has MATCHA learned?"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM knowledge")
        total_facts = cursor.fetchone()[0]
        cursor = self.conn.execute("SELECT COUNT(*) FROM topic_interest")
        total_topics = cursor.fetchone()[0]
        cursor = self.conn.execute("SELECT topic, count FROM topic_interest ORDER BY count DESC LIMIT 5")
        top_topics = cursor.fetchall()
        return {
            "total_facts": total_facts,
            "total_topics": total_topics,
            "top_topics": top_topics,
        }
