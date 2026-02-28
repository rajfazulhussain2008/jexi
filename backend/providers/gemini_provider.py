import asyncio
from providers.base import BaseProvider


GEMINI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


class GeminiProvider(BaseProvider):
    """Provider for Google Gemini API using the official SDK."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        # We configure it right away, but if we have multiple instances we might just
        # need to configure it per call, or pass it to individual calls.
        # Since google-generativeai is module-level configured by genai.configure, 
        # it might be tricky to have multiple concurrent keys unless handled via 
        # GenerativeModel initialization or passing `api_key` parameter (if supported).
        # We will use `genai.configure(api_key=...)` in a thread or directly, 
        # but to be thread-safe we can pass credentials/api_key if the SDK allows.
        # However, the SDK might not expose it easily. Instead, if we only have one or we change it:
        # For simplicity in this prompt, we'll set it here.
        # If rotation is needed, we'll need to set it before using, but it's module-global.

    @property
    def name(self) -> str:
        return "gemini"

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        used_model = model or GEMINI_MODELS[0]
        try:
            import google.generativeai as genai
            # We must configure it before the call, in case another instance changed it
            genai.configure(api_key=self.api_key)
            
            # Extract system instruction
            system_instruction = None
            history = []
            last_message = ""

            for msg in messages:
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                elif msg["role"] == "user":
                    history.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    history.append({"role": "model", "parts": [msg["content"]]})

            # The last message typically is from user and we don't put it in history
            # if we are doing a standard generate_content, but if using chat session:
            if history and history[-1]["role"] == "user":
                last_message = history[-1]["parts"][0]
                history = history[:-1]

            g_model = genai.GenerativeModel(
                model_name=used_model,
                system_instruction=system_instruction
            )
            
            chat_session = g_model.start_chat(history=history)

            # Create sending coroutine
            response_coro = chat_session.send_message_async(content=last_message)
            # Apply 30s timeout manually using asyncio
            response = await asyncio.wait_for(response_coro, timeout=30.0)

            text = response.text
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
