from .openai_compatible import OpenAICompatibleProvider

_MODEL_MAP = {
    "cerebras-llama-3.3-70b": "llama3.3-70b",
}


class CerebrasProvider(OpenAICompatibleProvider):
    def __init__(self):
        super().__init__(
            name="cerebras",
            api_key_env="CEREBRAS_API_KEY",
            base_url="https://api.cerebras.ai/v1",
            model_map=_MODEL_MAP,
        )
