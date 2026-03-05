"""
MATCHA Thinker — Human-like reasoning via web intelligence.
No paid APIs. Uses DDG Instant + Wikipedia + Brave web snippets.
"""

import requests
import re
import html
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
TIMEOUT = 6


class Thinker:
    """
    Web-powered reasoning engine.
    Sources: DDG Instant Answers, Wikipedia, Brave web snippets.
    Returns natural, concise human-like answers.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        print("[MATCHA Thinker] Web reasoning engine ready.")

    def think(self, query: str) -> str:
        q = query.strip()

        # 1. DDG Instant for short factual questions (capitals, dates, quick facts)
        if re.search(r'\b(capital of|capital city|president of|prime minister of|population of|how many|how old|when was|born in|year)\b', q.lower()):
            answer = self._ddg_instant(q)
            if answer and len(answer) > 10:
                return self._trim(answer)

        # 2. Wikipedia for concept/person/place questions
        if self._is_wiki_query(q):
            answer = self._wikipedia(q)
            if answer and len(answer) > 30:
                return self._trim(answer)

        # 3. DDG Instant fallback
        answer = self._ddg_instant(q)
        if answer and len(answer) > 30:
            return self._trim(answer)

        # 4. Brave web snippets (how-to, opinions, current events, anything)
        answer = self._brave_snippets(q)
        if answer and len(answer) > 30:
            return self._trim(answer)

        return "I searched but couldn't get a clear answer on that. Try rephrasing."

    # ── Sources ────────────────────────────────────────────────────────────

    def _ddg_instant(self, query: str) -> str:
        """DuckDuckGo Instant Answer API — zero-click info."""
        try:
            url = (
                "https://api.duckduckgo.com/?q="
                + urllib.parse.quote(query)
                + "&format=json&no_html=1&skip_disambig=1"
            )
            r = self.session.get(url, timeout=TIMEOUT)
            d = r.json()

            # Direct abstract
            abstract = d.get("AbstractText", "").strip()
            if abstract and len(abstract) > 30:
                return abstract

            # Answer field (short factual)
            answer = d.get("Answer", "").strip()
            if answer:
                return answer

            # Definition
            definition = d.get("Definition", "").strip()
            if definition:
                return definition

            # Related topics
            related = d.get("RelatedTopics", [])
            texts = []
            for rt in related[:3]:
                if isinstance(rt, dict) and rt.get("Text"):
                    texts.append(rt["Text"])
            if texts:
                return " ".join(texts[:2])

            return ""
        except:
            return ""

    def _is_wiki_query(self, q: str) -> bool:
        """Should we try Wikipedia for this?"""
        q_lower = q.lower()
        return bool(re.search(
            r'\b(what is|what are|who is|who was|who were|where is|when (did|was|is)|'
            r'how does|explain|define|tell me about|history of|origin of)\b',
            q_lower
        ))

    def _wikipedia(self, query: str) -> str:
        """Wikipedia summary API."""
        try:
            # Disambiguate common query types
            search_query = query
            if re.search(r'\bframework\b', query, re.I):
                search_query = re.sub(r'\b(what is|the|a)\b', '', query, flags=re.I).strip() + " software"
            elif re.search(r'\bprogramming language\b', query, re.I):
                search_query = re.sub(r'\b(what is|the|a)\b', '', query, flags=re.I).strip()

            # Search first
            search_url = (
                "https://en.wikipedia.org/w/api.php?action=query&list=search"
                "&srsearch=" + urllib.parse.quote(search_query)
                + "&srlimit=1&format=json"
            )
            r = self.session.get(search_url, timeout=TIMEOUT)
            results = r.json().get("query", {}).get("search", [])
            if not results:
                return ""

            # Get the top result's summary
            title = results[0]["title"]
            summary_url = (
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + urllib.parse.quote(title.replace(" ", "_"))
            )
            r = self.session.get(summary_url, timeout=TIMEOUT)
            d = r.json()
            extract = d.get("extract", "").strip()
            if extract:
                sentences = re.split(r'(?<=[.!?])\s+', extract)
                return " ".join(sentences[:3])
            return ""
        except:
            return ""

    def _brave_snippets(self, query: str) -> str:
        """Scrape Brave search result snippets."""
        try:
            url = (
                "https://search.brave.com/search?q="
                + urllib.parse.quote(query)
                + "&source=web"
            )
            r = self.session.get(url, timeout=TIMEOUT)
            soup = BeautifulSoup(r.text, "lxml")

            # Collect meaningful p tag text
            snippets = []
            for p in soup.find_all("p"):
                text = p.get_text(separator=" ", strip=True)
                text = html.unescape(text)
                # Filter: must be a real sentence, not nav/UI text
                if (len(text) > 40 and
                        not re.match(r'^(sign|log|click|subscribe|cookie|privacy|terms|menu|nav)', text, re.I) and
                        re.search(r'[a-zA-Z]{4,}', text)):
                    snippets.append(text)
                if len(snippets) >= 6:
                    break

            if not snippets:
                return ""

            # Score sentences by relevance to query
            query_words = set(re.sub(r'[^a-z\s]', '', query.lower()).split())
            stop = {"what", "is", "are", "the", "a", "an", "how", "why",
                    "who", "when", "where", "does", "do", "can", "i", "you",
                    "to", "of", "in", "it", "that", "this", "for", "with"}
            query_words -= stop

            scored = []
            for snippet in snippets:
                words = set(re.sub(r'[^a-z\s]', '', snippet.lower()).split())
                score = len(words & query_words)
                scored.append((score, snippet))

            scored.sort(reverse=True)

            # Take the best 2 snippets and join naturally
            top = [s for _, s in scored[:2] if _]
            if not top:
                top = snippets[:2]

            combined = " ".join(top)
            return combined

        except:
            return ""

    # ── Formatter ─────────────────────────────────────────────────────────

    def _trim(self, text: str, max_len: int = 380) -> str:
        """Clean up and trim to a readable length."""
        if not text:
            return ""

        text = text.strip()
        # Remove HTML tags if any slipped through
        text = re.sub(r'<[^>]+>', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Unescape HTML entities
        text = html.unescape(text)

        if len(text) <= max_len:
            return text

        # Cut at sentence boundary
        cut = text[:max_len]
        last_dot = max(cut.rfind('.'), cut.rfind('!'), cut.rfind('?'))
        if last_dot > 80:
            return cut[:last_dot + 1]
        return cut.rstrip() + "..."
