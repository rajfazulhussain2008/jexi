"""
cache_service.py — LLM Response Caching
In-memory cache keyed by SHA-256 of (system_prompt + user_message + model).
Supports TTL-based expiry and hit-rate statistics.
"""

import hashlib
import sys
import time


class ResponseCache:
    """In-memory LLM response cache with TTL and hit tracking."""

    def __init__(self):
        # hash → {response, timestamp, ttl, hit_count}
        self._cache: dict[str, dict] = {}
        self._hits: int = 0
        self._misses: int = 0

    # ------------------------------------------------------------------
    @staticmethod
    def _hash(system_prompt: str, user_message: str, model: str) -> str:
        """SHA-256 of concatenated inputs."""
        raw = f"{system_prompt}||{user_message}||{model}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    def get(self, system_prompt: str, user_message: str, model: str) -> dict | None:
        """Return cached response or None on miss / expiry."""
        try:
            key = self._hash(system_prompt, user_message, model)
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None

            age = time.time() - entry["timestamp"]
            if age > entry["ttl"]:
                del self._cache[key]
                self._misses += 1
                return None

            entry["hit_count"] += 1
            self._hits += 1
            return entry["response"]
        except Exception:
            self._misses += 1
            return None

    # ------------------------------------------------------------------
    def set(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        response: dict,
        ttl_seconds: int = 3600,
    ):
        """Store a response with a TTL (seconds). ttl_seconds=0 → don't cache."""
        if ttl_seconds <= 0:
            return
        try:
            key = self._hash(system_prompt, user_message, model)
            self._cache[key] = {
                "response": response,
                "timestamp": time.time(),
                "ttl": ttl_seconds,
                "hit_count": 0,
            }
        except Exception:
            pass

    # ------------------------------------------------------------------
    def clear_expired(self):
        """Evict all entries past their TTL."""
        now = time.time()
        expired = [
            k for k, v in self._cache.items()
            if now - v["timestamp"] > v["ttl"]
        ]
        for k in expired:
            del self._cache[k]

    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        """Cache statistics: entries, hit rate, estimated memory."""
        total_lookups = self._hits + self._misses
        return {
            "total_entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total_lookups, 4) if total_lookups else 0.0,
            "estimated_memory_bytes": sys.getsizeof(self._cache),
        }
