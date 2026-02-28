import httpx
from providers.base import BaseProvider


HF_MODELS = {
    "mistral": "mistralai/Mistral-7B-Instruct-v0.3",
    "zephyr": "HuggingFaceH4/zephyr-7b-beta",
    "phi": "microsoft/Phi-3-mini-4k-instruct"
}


class HuggingFaceProvider(BaseProvider):
    """Provider for HuggingFace Inference API."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "huggingface"

    def _format_prompt(self, messages: list[dict], model_key: str) -> str:
        prompt = ""
        # Extremely basic ChatML/Instruct template matching typical requirements
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                # For zephyr
                prompt += f"<|system|>\n{content}</s>\n"
            elif role == "user":
                if model_key == "mistral":
                    prompt += f"[INST] {content} [/INST]"
                else:
                    prompt += f"<|user|>\n{content}</s>\n"
            elif role == "assistant":
                if model_key != "mistral":
                    prompt += f"<|assistant|>\n{content}</s>\n"
        
        # Finally trigger generation for zephyr/phi if it's not mistral
        if model_key != "mistral" and messages[-1]["role"] != "assistant":
             prompt += "<|assistant|>\n"
             
        return prompt

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        model_key = model if model in HF_MODELS else "mistral"
        model_id = HF_MODELS.get(model_key, HF_MODELS["mistral"])
        endpoint = f"https://api-inference.huggingface.co/models/{model_id}"
        
        try:
            prompt = self._format_prompt(messages, model_key)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 500,
                    "temperature": 0.7
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(endpoint, headers=headers, json=body)
                response.raise_for_status()
                data = response.json()
                
                # Inference API usually returns a list with a dictionary
                raw_text = None
                if isinstance(data, list) and len(data) > 0 and "generated_text" in data[0]:
                    raw_text = data[0]["generated_text"]
                elif isinstance(data, dict) and "generated_text" in data:
                    raw_text = data["generated_text"]
                elif "error" in data:
                    raise Exception(data["error"])
                
                text = None
                if raw_text is not None:
                    # Clean response: remove prompt from generated text
                    if raw_text.startswith(prompt):
                        text = raw_text[len(prompt):].strip()
                    else:
                        text = raw_text.strip()

            return {
                "text": text,
                "provider": self.name,
                "model": model_key,
                "status": "success",
                "error": None,
            }
        except httpx.TimeoutException:
            return {
                "text": None,
                "provider": self.name,
                "model": model_key,
                "status": "failed",
                "error": "Timeout",
            }
        except Exception as e:
            return {
                "text": None,
                "provider": self.name,
                "model": model_key,
                "status": "failed",
                "error": str(e),
            }
