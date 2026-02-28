"""
key_manager.py — API Key Rotation Manager
Manages multiple API keys per LLM provider with round-robin rotation,
exhaustion tracking, and automatic daily resets.
"""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from datetime import datetime, timezone, date

from config import (
    GROQ_API_KEYS, GEMINI_API_KEYS, COHERE_API_KEYS,
    OPENROUTER_API_KEYS, HF_API_KEYS, CLOUDFLARE_API_KEYS,
    NVIDIA_API_KEYS, SAMBANOVA_API_KEYS, CEREBRAS_API_KEYS,
    JWT_SECRET
)


class KeyManager:
    """Round-robin API key rotation with exhaustion tracking and DB encryption."""

    def __init__(self):
        self._current_index: dict[str, int] = {}
        self._last_reset: date = date.today()
        self.keys: dict[str, list[dict]] = {}
        
        # Setup encryption for shared keys from friends
        salt = b'jexi_encryption_salt' # In production, this should ideally be another env var
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(JWT_SECRET.encode()))
        self.fernet = Fernet(key)

        provider_key_map = {
            "groq": GROQ_API_KEYS,
            "gemini": GEMINI_API_KEYS,
            "cohere": COHERE_API_KEYS,
            "openrouter": OPENROUTER_API_KEYS,
            "huggingface": HF_API_KEYS,
            "cloudflare": CLOUDFLARE_API_KEYS,
            "nvidia": NVIDIA_API_KEYS,
            "sambanova": SAMBANOVA_API_KEYS,
            "cerebras": CEREBRAS_API_KEYS,
        }

        for provider, raw_keys in provider_key_map.items():
            self.keys[provider] = [
                {
                    "key": k,
                    "is_exhausted": False,
                    "requests_today": 0,
                    "last_used": None,
                    "exhausted_at": None,
                    "is_shared": False # Keys from .env are not marked as shared
                }
                for k in raw_keys
            ]
            self._current_index[provider] = 0

    def encrypt_key(self, plain_text_key: str) -> str:
        """Encrypts a string for DB storage."""
        return self.fernet.encrypt(plain_text_key.encode()).decode()

    def decrypt_key(self, encrypted_key: str) -> str:
        """Decrypts a string from the DB."""
        return self.fernet.decrypt(encrypted_key.encode()).decode()

    def add_db_keys(self, shared_keys_from_db: list):
        """Merges keys from the database (offered by friends) into the rotation pool."""
        for sk in shared_keys_from_db:
            if not sk.is_active: continue
            
            provider = sk.provider.lower()
            if provider not in self.keys:
                self.keys[provider] = []
                self._current_index[provider] = 0
            
            # Check if key already in pool to avoid duplicates
            decrypted = self.decrypt_key(sk.encrypted_key)
            if any(k["key"] == decrypted for k in self.keys[provider]):
                continue

            self.keys[provider].append({
                "key": decrypted,
                "is_exhausted": sk.is_exhausted,
                "requests_today": 0,
                "last_used": sk.last_used.isoformat() if sk.last_used else None,
                "exhausted_at": sk.exhausted_at.isoformat() if sk.exhausted_at else None,
                "is_shared": True,
                "db_id": sk.id
            })


    # ------------------------------------------------------------------
    def _maybe_reset(self):
        """Auto-reset all keys if the day has rolled over."""
        today = date.today()
        if today != self._last_reset:
            self.reset_daily()
            self._last_reset = today

    # ------------------------------------------------------------------
    def get_next_key(self, provider: str) -> str | None:
        """Return the next non-exhausted key for *provider* (round-robin).
        Returns None if every key is exhausted or no keys exist."""
        try:
            self._maybe_reset()
            entries = self.keys.get(provider, [])
            if not entries:
                return None

            total = len(entries)
            start = self._current_index.get(provider, 0) % total
            for offset in range(total):
                idx = (start + offset) % total
                entry = entries[idx]
                if not entry["is_exhausted"]:
                    entry["requests_today"] += 1
                    entry["last_used"] = datetime.now(timezone.utc).isoformat()
                    self._current_index[provider] = (idx + 1) % total
                    return entry["key"]
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    def mark_exhausted(self, provider: str, key_index: int):
        """Mark a specific key as exhausted (e.g. after a 429 response)."""
        try:
            entries = self.keys.get(provider, [])
            if 0 <= key_index < len(entries):
                entries[key_index]["is_exhausted"] = True
                entries[key_index]["exhausted_at"] = datetime.now(timezone.utc).isoformat()
        except Exception:
            pass

    def mark_exhausted_by_value(self, provider: str, key_value: str):
        """Mark a key as exhausted by its actual string value."""
        try:
            for entry in self.keys.get(provider, []):
                if entry["key"] == key_value:
                    entry["is_exhausted"] = True
                    entry["exhausted_at"] = datetime.now(timezone.utc).isoformat()
                    break
        except Exception:
            pass

    # ------------------------------------------------------------------
    def reset_daily(self):
        """Reset all exhaustion flags and daily counters."""
        for provider_entries in self.keys.values():
            for entry in provider_entries:
                entry["is_exhausted"] = False
                entry["requests_today"] = 0
                entry["exhausted_at"] = None

    # ------------------------------------------------------------------
    def get_key_stats(self) -> dict:
        """Return usage statistics per provider."""
        stats: dict = {}
        for provider, entries in self.keys.items():
            stats[provider] = {
                "total_keys": len(entries),
                "active_keys": sum(1 for e in entries if not e["is_exhausted"]),
                "total_requests_today": sum(e["requests_today"] for e in entries),
                "keys": [
                    {
                        "index": i,
                        "requests_today": e["requests_today"],
                        "is_exhausted": e["is_exhausted"],
                        "last_used": e["last_used"],
                    }
                    for i, e in enumerate(entries)
                ],
            }
        return stats

    # ------------------------------------------------------------------
    def get_active_key_count(self, provider: str) -> int:
        """How many non-exhausted keys remain for a provider."""
        try:
            return sum(
                1 for e in self.keys.get(provider, []) if not e["is_exhausted"]
            )
        except Exception:
            return 0
