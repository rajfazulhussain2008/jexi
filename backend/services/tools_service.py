"""
tools_service.py — External Web APIs & Caching
Static stateless wrappers connecting to public, non-authenticated tools 
utilized by morning briefings and chat prompts dynamically.
"""

import urllib.request
import urllib.parse
import json
import time

try:
    import feedparser
except ImportError:
    pass  # Allow system to run if pip is missing


class ToolsService:
    
    _cache = {} # memory mapped rudimentary cache format: URL -> (time, json)
    
    @staticmethod
    def _fetch(url: str, ttl: int = 3600) -> dict | None:
        """Generic cached getter mapping to JSON."""
        now = time.time()
        if url in ToolsService._cache:
            stamp, data = ToolsService._cache[url]
            if now - stamp < ttl:
                return data

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'JEXI-Terminal/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                ToolsService._cache[url] = (now, result)
                return result
        except Exception as e:
            return None

    @staticmethod
    def get_weather(city: str = "London") -> dict | None:
        """Returns minimal JSON structure of current weather using WTTR."""
        try:
            # wttr format j1 exposes current_condition block
            raw = ToolsService._fetch(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1", ttl=3600)
            if not raw or "current_condition" not in raw: return None
            
            cond = raw["current_condition"][0]
            return {
                "temp": cond.get("temp_C", ""),
                "feels_like": cond.get("FeelsLikeC", ""),
                "description": cond.get("weatherDesc", [{}])[0].get("value", ""),
                "humidity": cond.get("humidity", ""),
                "wind": cond.get("windspeedKmph", "")
            }
        except:
            return None

    @staticmethod
    def get_news(topic: str = "technology", count: int = 5) -> list:
        """RSS scrape of google news parsing feed headers."""
        try:
            if "feedparser" not in globals():
                return [] # Module missing fallback
            d = feedparser.parse(f"https://news.google.com/rss/search?q={urllib.parse.quote(topic)}")
            results = []
            for entry in d.entries[:count]:
                results.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published
                })
            return results
        except:
            return []

    @staticmethod
    def get_wiki(query: str) -> dict | None:
        """Query standard wikipedia rest v1 summary API."""
        try:
            raw = ToolsService._fetch(f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}", ttl=86400)
            if not raw: return None
            return {
                "title": raw.get("title", ""),
                "summary": raw.get("extract", ""),
                "url": raw.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        except:
            return None

    @staticmethod
    def get_quote() -> str | None:
        try:
            raw = ToolsService._fetch("https://api.quotable.io/random", ttl=60)
            if not raw: return None
            return f'"{raw.get("content", "")}" - {raw.get("author", "Unknown")}'
        except:
            return None

    @staticmethod
    def get_joke() -> str | None:
        try:
            raw = ToolsService._fetch("https://official-joke-api.appspot.com/random_joke", ttl=60)
            if not raw: return None
            return f'{raw.get("setup", "")} ... {raw.get("punchline", "")}'
        except:
            return None

    @staticmethod
    def search(query: str) -> dict | None:
        """DuckDuckGo basic snippet summary lookup."""
        try:
            raw = ToolsService._fetch(f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json", ttl=3600)
            if not raw: return None
            return {
                "abstract": raw.get("AbstractText", ""),
                "url": raw.get("AbstractURL", ""),
                "related_topics": [t.get("Text", "") for t in raw.get("RelatedTopics", []) if "Text" in t][:3]
            }
        except:
            return None
