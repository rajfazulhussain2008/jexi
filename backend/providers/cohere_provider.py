import asyncio
from providers.base import BaseProvider


COHERE_MODELS = [
    "command-r-plus",
    "command-r",
    "command-a-03-2025"
]

class CohereProvider(BaseProvider):
    """Provider for Cohere API (v2 client)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        try:
            import cohere
            self.client = cohere.AsyncClientV2(api_key=api_key, timeout=30.0)
        except ImportError:
            self.client = None

    @property
    def name(self) -> str:
        return "cohere"

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        used_model = model or COHERE_MODELS[0]
        try:
            # v2 chat uses messages format naturally aligned mostly with OpenAI format.
            # {"role": "system", "content": "..."}, {"role": "user", "content": "..."}
            
            async def _chat():
                return await self.client.chat(
                    model=used_model,
                    messages=messages
                )
                
            response = await asyncio.wait_for(_chat(), timeout=30.0)
            
            text = response.message.content[0].text if response.message.content else None

            return {
                "text": text,
                "provider": self.name,
                "model": used_model,
                "status": "success",
                "error": None,
            }
        except asyncio.TimeoutError:
            return {
                "text": None,
                "provider": self.name,
                "model": used_model,
                "status": "failed",
                "error": "Timeout",
            }
        except Exception as e:
            return {
                "text": None,
                "provider": self.name,
                "model": used_model,
                "status": "failed",
                "error": str(e),
            }
