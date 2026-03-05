"""
MATCHA Web Agent — Online Mode v2
Web-powered intelligence with zero paid APIs.
"""

import requests
import json
import re
import urllib.parse
from bs4 import BeautifulSoup
import feedparser
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 4


class WebAgent:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        print("[MATCHA Web Agent] Online mode ready.")

    def search(self, query: str, max_results: int = 5) -> dict:
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            results = []
            for item in soup.select(".result__body")[:max_results]:
                title_el = item.select_one(".result__title")
                snippet_el = item.select_one(".result__snippet")
                link_el = item.select_one(".result__url")
                title = title_el.get_text(strip=True) if title_el else ""
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                url_text = link_el.get_text(strip=True) if link_el else ""
                if title:
                    results.append({"title": title, "snippet": snippet, "url": url_text})
            if results:
                top = results[0]
                summary = f"Top result: {top['title']}."
                if top["snippet"]:
                    summary += f" {top['snippet']}"
                return {"success": True, "results": results, "summary": summary}
            return {"success": False, "error": "No results found.", "results": []}
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}

    def get_weather(self, location: str = "London") -> dict:
        try:
            url = f"https://wttr.in/{urllib.parse.quote(location)}?format=j1"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            current = data["current_condition"][0]
            weather_desc = current["weatherDesc"][0]["value"]
            temp_c = current["temp_C"]
            feels_c = current["FeelsLikeC"]
            humidity = current["humidity"]
            wind_kmph = current["windspeedKmph"]
            today = data["weather"][0]
            max_c = today["maxtempC"]
            min_c = today["mintempC"]
            summary = (
                f"{location}: {weather_desc}, {temp_c}degC "
                f"(feels {feels_c}degC). "
                f"High {max_c}degC, low {min_c}degC. "
                f"Humidity {humidity}%, wind {wind_kmph} km/h."
            )
            return {
                "success": True, "location": location, "temp_c": temp_c,
                "description": weather_desc, "summary": summary
            }
        except Exception as e:
            return {"success": True, "summary": f"Weather for {location} is unavailable right now. Try again shortly."}

    def get_news(self, source: str = "bbc", max_articles: int = 5) -> dict:
        feeds = {
            "bbc": "https://feeds.bbci.co.uk/news/rss.xml",
            "reuters": "https://feeds.reuters.com/reuters/topNews",
            "guardian": "https://www.theguardian.com/uk/rss",
            "techcrunch": "https://techcrunch.com/feed/",
        }
        feed_url = feeds.get(source.lower(), feeds["bbc"])
        try:
            feed = feedparser.parse(feed_url)
            articles = []
            for entry in feed.entries[:max_articles]:
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200],
                    "link": entry.get("link", "")
                })
            if articles:
                headlines = ". ".join([a["title"] for a in articles[:3]])
                summary = f"Top headlines from {source.upper()}: {headlines}."
                return {"success": True, "articles": articles, "summary": summary}
            return {"success": False, "error": "No articles retrieved."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_youtube(self, query: str, max_results: int = 5) -> dict:
        try:
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            pattern = r'var ytInitialData = ({.*?});</script>'
            match = re.search(pattern, resp.text, re.DOTALL)
            videos = []
            if match:
                try:
                    data = json.loads(match.group(1))
                    contents = (
                        data.get("contents", {})
                        .get("twoColumnSearchResultsRenderer", {})
                        .get("primaryContents", {})
                        .get("sectionListRenderer", {})
                        .get("contents", [])
                    )
                    for section in contents:
                        items = section.get("itemSectionRenderer", {}).get("contents", [])
                        for item in items:
                            vr = item.get("videoRenderer", {})
                            if vr:
                                title = vr.get("title", {}).get("runs", [{}])[0].get("text", "")
                                video_id = vr.get("videoId", "")
                                channel = vr.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                                duration = vr.get("lengthText", {}).get("simpleText", "")
                                if title and video_id:
                                    videos.append({
                                        "title": title,
                                        "url": f"https://www.youtube.com/watch?v={video_id}",
                                        "channel": channel, "duration": duration
                                    })
                                if len(videos) >= max_results:
                                    break
                except json.JSONDecodeError:
                    pass
            if videos:
                top = videos[0]
                summary = f"Top YouTube result: '{top['title']}' by {top['channel']}. {top['url']}"
                return {"success": True, "videos": videos, "summary": summary}
            return {"success": False, "error": "No videos found.", "videos": []}
        except Exception as e:
            return {"success": False, "error": str(e), "videos": []}

    def wikipedia(self, query: str) -> dict:
        try:
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {"action":"query","list":"search","srsearch":query,"format":"json","utf8":1,"srlimit":1}
            resp = self.session.get(search_url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            results = resp.json().get("query", {}).get("search", [])
            if not results:
                return {"success": False, "error": f"No Wikipedia article for '{query}'."}
            title = results[0]["title"]
            extract_params = {"action":"query","prop":"extracts","exintro":True,"explaintext":True,"titles":title,"format":"json","utf8":1}
            resp2 = self.session.get(search_url, params=extract_params, timeout=TIMEOUT)
            resp2.raise_for_status()
            pages = resp2.json().get("query", {}).get("pages", {})
            page = next(iter(pages.values()))
            extract = page.get("extract", "")
            sentences = re.split(r'(?<=[.!?])\s+', extract)
            summary_text = " ".join(sentences[:3])
            return {
                "success": True, "title": title,
                "summary": f"{title}: {summary_text}",
                "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ','_'))}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_url(self, url: str) -> dict:
        try:
            if not url.startswith("http"):
                url = "https://" + url
            resp = self.session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script","style","nav","footer","header","aside"]):
                tag.decompose()
            title = soup.title.get_text(strip=True) if soup.title else url
            content_el = soup.find("article") or soup.find("main") or soup.body
            text = content_el.get_text(separator="\n", strip=True)[:2000] if content_el else ""
            text = re.sub(r'\n{3,}', '\n\n', text)
            summary = text[:300].replace("\n"," ") + "..." if len(text) > 300 else text
            return {"success": True, "url": url, "title": title, "content": text, "summary": f"{title}: {summary}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def handle_query(self, query: str, intent_hint: str = "") -> dict:
        query_lower = query.lower()
        if any(w in query_lower for w in ["weather","temperature","forecast","rain"]):
            location = self._extract_location(query) or "London"
            return self.get_weather(location)
        elif any(w in query_lower for w in ["news","headlines","latest"]):
            source = "bbc"
            if "techcrunch" in query_lower or "tech" in query_lower:
                source = "techcrunch"
            return self.get_news(source)
        elif any(w in query_lower for w in ["youtube","video","watch"]):
            for prefix in ["youtube","find video","search youtube","watch"]:
                if prefix in query_lower:
                    q = query_lower.split(prefix,1)[-1].strip()
                    if q:
                        return self.search_youtube(q)
            return self.search_youtube(query)
        elif any(w in query_lower for w in ["what is","who is","wikipedia","tell me about","explain"]):
            topic = query
            for prefix in ["what is","who is","tell me about","explain","wikipedia"]:
                if prefix in query_lower:
                    topic = query_lower.split(prefix,1)[-1].strip()
                    break
            return self.wikipedia(topic)
        elif re.search(r'https?://|www\.', query_lower):
            url_match = re.search(r'(https?://[^\s]+|www\.[^\s]+)', query)
            if url_match:
                return self.fetch_url(url_match.group(1))
        return self.search(query)

    def _extract_location(self, text: str) -> Optional[str]:
        patterns = [
            r'weather (?:in|for|at) ([A-Za-z\s]+)',
            r'(?:in|at|for) ([A-Za-z\s]+) weather',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None


if __name__ == "__main__":
    agent = WebAgent()
    print("Weather:", agent.get_weather("London").get("summary"))
    print("Wiki:", agent.wikipedia("Python").get("summary","")[:100])
    print("News:", agent.get_news("bbc").get("summary","")[:100])
