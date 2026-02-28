import httpx
from providers.base import BaseProvider


CF_MODELS = [
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/mistral/mistral-7b-instruct-v0.2"
]


class CloudflareProvider(BaseProvider):
    """Provider for Cloudflare Workers AI."""

    def __init__(self, api_key: str, account_id: str):
        self.api_key = api_key
        self.account_id = account_id

    @property
    def name(self) -> str:
        return "cloudflare"

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        used_model = model or CF_MODELS[0]
        endpoint = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run/{used_model}"
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "messages": messages
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                text = None
                
                # Cloudflare AI response structure
                if data.get("success") and "result" in data:
                    text = data["result"].get("response")

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
