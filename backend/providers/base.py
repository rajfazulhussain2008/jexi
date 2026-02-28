from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Abstract base class for all AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of this provider (e.g. 'groq', 'gemini')."""
        ...

    @abstractmethod
    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        """
        Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            model: Optional model identifier. Provider uses its default if None.

        Returns:
            dict with keys:
                - text: str | None  — the generated text
                - provider: str     — provider name
                - model: str        — model used
                - status: "success" | "failed"
                - error: str | None — error message on failure
        """
        ...
