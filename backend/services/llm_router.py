"""
llm_router.py — Smart Multi-LLM Router
Routes AI requests to the best available provider with automatic fallback,
key rotation, caching, response-time tracking, and per-provider scoring.
"""

import time
from datetime import datetime, timezone

from services.key_manager import KeyManager
from services.cache_service import ResponseCache
from models.api_usage import APIUsage

# Provider imports — each exposes an async chat(messages, model) method
from providers.groq_provider import GroqProvider
from providers.gemini_provider import GeminiProvider
from providers.cohere_provider import CohereProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.huggingface_provider import HuggingFaceProvider
from providers.cloudflare_provider import CloudflareProvider
from providers.nvidia_provider import NVIDIAProvider
from providers.sambanova_provider import SambaNovaProvider
from providers.cerebras_provider import CerebrasProvider


# Default priority order (lower = tried first)
_DEFAULT_PROVIDERS = [
    {"name": "groq",        "provider_class": GroqProvider,        "priority": 1},
    {"name": "cerebras",    "provider_class": CerebrasProvider,    "priority": 2},
    {"name": "sambanova",   "provider_class": SambaNovaProvider,   "priority": 3},
    {"name": "gemini",      "provider_class": GeminiProvider,      "priority": 4},
    {"name": "nvidia",      "provider_class": NVIDIAProvider,      "priority": 5},
    {"name": "cloudflare",  "provider_class": CloudflareProvider,  "priority": 6},
    {"name": "cohere",      "provider_class": CohereProvider,      "priority": 7},
    {"name": "openrouter",  "provider_class": OpenRouterProvider,  "priority": 8},
    {"name": "huggingface", "provider_class": HuggingFaceProvider, "priority": 9},
]


class LLMRouter:
    """Route AI requests to the best available LLM provider."""

    def __init__(self, db_session=None):
        self.key_manager = key_manager # reference to the global singleton
        self.cache = ResponseCache()
        self.db_session = db_session

        # Try to load existing keys from the database on startup
        if self.db_session:
            try:
                from models.shared_key import SharedKey
                shared = self.db_session.query(SharedKey).filter(SharedKey.is_active == True).all()
                if shared:
                    self.key_manager.add_db_keys(shared)
            except Exception as e:
                print(f"Warning: Could not load keys from database on start: {e}")

        # Build mutable provider registry
        self.providers: list[dict] = []
        for p in _DEFAULT_PROVIDERS:
            # Only include providers that have at least one key configured
            if self.key_manager.keys.get(p["name"]):
                self.providers.append({
                    "name": p["name"],
                    "provider_class": p["provider_class"],
                    "priority": p["priority"],
                    "failure_count": 0,
                    "avg_response_time": 0.0,
                    "total_calls": 0,
                    "last_used": None,
                })

    # ------------------------------------------------------------------
    def _score(self, entry: dict) -> float:
        """Score a provider — lower is better."""
        return (
            entry["priority"]
            + (entry["failure_count"] * 5)
            + (entry["avg_response_time"] * 0.1)
        )

    # ------------------------------------------------------------------
    def _log_usage(self, provider: str, model: str | None, response_time: float,
                   success: bool, error: str | None = None):
        """Persist an API call record to the database."""
        try:
            if self.db_session is None:
                return
            record = APIUsage(
                provider=provider,
                model=model,
                response_time=response_time,
                success=success,
                error=error,
                created_at=datetime.now(timezone.utc),
            )
            self.db_session.add(record)
            self.db_session.commit()
        except Exception:
            try:
                self.db_session.rollback()
            except Exception:
                pass

    # ------------------------------------------------------------------
    async def route(
        self,
        messages: list,
        preferred_provider: str | None = None,
        model: str | None = None,
        cache_ttl: int = 0,
    ) -> dict:
        """Route a chat request through available providers with fallback.

        Parameters
        ----------
        messages : list
            OpenAI-style list of {role, content} dicts.
        preferred_provider : str, optional
            If set, this provider is tried first regardless of score.
        model : str, optional
            Model override passed to the provider.
        cache_ttl : int
            Seconds to cache the response (0 = no cache).

        Returns
        -------
        dict  with keys: text, provider, model, status, error, response_time, cached
        """
        # --- 1. Cache check ----
        if cache_ttl > 0:
            system_prompt = ""
            user_message = ""
            for m in messages:
                if m.get("role") == "system":
                    system_prompt = m.get("content", "")
                elif m.get("role") == "user":
                    user_message = m.get("content", "")
            cached = self.cache.get(system_prompt, user_message, model or "")
            if cached is not None:
                return {**cached, "cached": True}

        # --- 2. Sort providers by score ---
        ordered = sorted(self.providers, key=self._score)

        # --- 3. Preferred provider first ---
        if preferred_provider:
            preferred = [p for p in ordered if p["name"] == preferred_provider]
            others = [p for p in ordered if p["name"] != preferred_provider]
            ordered = preferred + others

        # --- 4. Try each provider ---
        last_error = "All providers failed"
        for entry in ordered:
            provider_name = entry["name"]

            # Try every available key for this provider
            while True:
                api_key = self.key_manager.get_next_key(provider_name)
                if api_key is None:
                    break  # all keys exhausted for this provider

                try:
                    provider_instance = entry["provider_class"](api_key=api_key)
                    t0 = time.time()
                    result = await provider_instance.chat(messages, model)
                    elapsed = round(time.time() - t0, 3)

                    if result.get("status") == "success":
                        # Update running averages
                        entry["total_calls"] += 1
                        entry["avg_response_time"] = round(
                            (entry["avg_response_time"] * (entry["total_calls"] - 1) + elapsed)
                            / entry["total_calls"],
                            3,
                        )
                        entry["failure_count"] = max(0, entry["failure_count"] - 1)
                        entry["last_used"] = datetime.now(timezone.utc).isoformat()

                        self._log_usage(provider_name, result.get("model"), elapsed, True)

                        # Cache if requested
                        if cache_ttl > 0:
                            system_prompt = ""
                            user_message = ""
                            for m in messages:
                                if m.get("role") == "system":
                                    system_prompt = m.get("content", "")
                                elif m.get("role") == "user":
                                    user_message = m.get("content", "")
                            self.cache.set(
                                system_prompt, user_message,
                                result.get("model", model or ""),
                                result, cache_ttl,
                            )

                        return {
                            "text": result.get("text", ""),
                            "provider": result.get("provider", provider_name),
                            "model": result.get("model", model),
                            "status": "success",
                            "error": None,
                            "response_time": elapsed,
                            "cached": False,
                        }

                    # Rate-limited (429)
                    error_msg = result.get("error", "")
                    if "429" in str(error_msg) or "rate" in str(error_msg).lower():
                        self.key_manager.mark_exhausted_by_value(provider_name, api_key)
                        continue  # try next key for same provider

                    # Other error — move on to next provider
                    entry["failure_count"] += 1
                    last_error = error_msg or f"{provider_name} returned an error"
                    self._log_usage(provider_name, model, 0, False, last_error)
                    break

                except Exception as exc:
                    entry["failure_count"] += 1
                    last_error = f"{provider_name}: {exc}"
                    self._log_usage(provider_name, model, 0, False, str(exc))
                    break  # move to next provider

        return {
            "text": f"I'm sorry, I couldn't process that right now. {last_error}",
            "provider": None,
            "model": None,
            "status": "error",
            "error": last_error,
            "response_time": 0,
            "cached": False,
        }

    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        """Aggregate API usage stats from the database."""
        try:
            if self.db_session is None:
                return {}
            from sqlalchemy import func
            rows = (
                self.db_session.query(
                    APIUsage.provider,
                    func.count(APIUsage.id).label("total_calls"),
                    func.avg(APIUsage.response_time).label("avg_time"),
                    func.sum(
                        func.cast(APIUsage.success, type_=None)
                    ).label("successes"),
                )
                .group_by(APIUsage.provider)
                .all()
            )
            stats = {}
            for row in rows:
                total = row.total_calls or 1
                stats[row.provider] = {
                    "total_calls": total,
                    "avg_response_time": round(float(row.avg_time or 0), 3),
                    "success_rate": round(float(row.successes or 0) / total, 4),
                }
            return stats
        except Exception:
            return {}

    # ------------------------------------------------------------------
    def get_provider_status(self) -> list:
        """Return current runtime status of every provider."""
        result = []
        for entry in self.providers:
            result.append({
                "name": entry["name"],
                "available_keys": self.key_manager.get_active_key_count(entry["name"]),
                "failure_count": entry["failure_count"],
                "avg_response_time": entry["avg_response_time"],
                "last_used": entry["last_used"],
                "priority": entry["priority"],
            })
        return result

    # ------------------------------------------------------------------
    def update_priority(self, provider_name: str, new_priority: int):
        """Change a provider's priority (lower = tried sooner)."""
        for entry in self.providers:
            if entry["name"] == provider_name:
                entry["priority"] = new_priority
                return True
        return False

# Singleton instance of KeyManager to be used throughout the app
key_manager = KeyManager()
_router_instance = None

def get_llm_router(db_session=None):
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter(db_session=db_session)
        # Point router to the singleton key_manager
        _router_instance.key_manager = key_manager

    # Give the instance the latest db session if provided
    if db_session:
        _router_instance.db_session = db_session
    return _router_instance
