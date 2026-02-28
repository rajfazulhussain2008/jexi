import httpx
from providers.base import BaseProvider


NVIDIA_MODELS = [
    "meta/llama-3.1-8b-instruct",
    "mistralai/mistral-7b-instruct-v0.3"
]


class NVIDIAProvider(BaseProvider):
    """Provider for NVIDIA NIM (OpenAI-compatible)."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://integrate.api.nvidia.com/v1/chat/completions"

    @property
    def name(self) -> str:
        return "nvidia"

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        used_model = model or NVIDIA_MODELS[0]
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": used_model,
                "messages": messages,
                "max_tokens": 1024,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.endpoint, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                text = data["choices"][0]["message"]["content"] if "choices" in data and data["choices"] else None

            return {
                "text": text,
                "provider": self.name,
                "model": used_model,
                "status": "success",
                "error": None,
            }
        except httpx.TimeoutException:
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
