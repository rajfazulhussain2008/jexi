import asyncio
from providers.base import BaseProvider


GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


class GroqProvider(BaseProvider):
    """Provider for Groq inference API using the official SDK."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            from groq import Groq
            self.client = Groq(api_key=api_key, timeout=30.0)
        except ImportError:
            self.client = None

    @property
    def name(self) -> str:
        return "groq"

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        used_model = model or GROQ_MODELS[0]
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=used_model,
                messages=messages,
                timeout=30.0,
            )
            text = response.choices[0].message.content if response.choices else None
            return {
                "text": text,
                "provider": self.name,
                "model": used_model,
                "status": "success",
                "error": None,
            }
        except Exception as e:
            return {
                "text": None,
                "provider": self.name,
                "model": used_model,
                "status": "failed",
                "error": str(e),
            }
