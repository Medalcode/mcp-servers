import logging

from .openai_compatible import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_MODEL_MAP = {
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "llama-3.1-8b": "llama-3.1-8b-instant",
    "mixtral-8x7b": "mixtral-8x7b-32768",
}


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="groq",
            api_key_env="GROQ_API_KEY",
            base_url="https://api.groq.com/openai/v1",
            model_map=_MODEL_MAP,
        )
