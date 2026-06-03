import json
import logging
import os
import time

import httpx

from .base import AIProvider, ProviderError, retry_ask

logger = logging.getLogger(__name__)

_MODEL_MAP = {
    "cerebras-llama-3.3-70b": "llama3.3-70b",
}


class CerebrasProvider(AIProvider):
    name = "cerebras"
    _CACHE_TTL = 60

    def __init__(self):
        self.api_key = os.environ.get("CEREBRAS_API_KEY", "")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._base_url = "https://api.cerebras.ai/v1"
        self._available_cache: bool | None = None
        self._available_cache_time: float = 0.0

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        now = time.monotonic()
        if self._available_cache is not None and now - self._available_cache_time < self._CACHE_TTL:
            return self._available_cache
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = await self._client.get(f"{self._base_url}/models", headers=headers)
            self._available_cache = resp.status_code == 200
            self._available_cache_time = now
            return self._available_cache
        except Exception:
            logger.exception("%s availability check failed", self.name)
            self._available_cache = False
            self._available_cache_time = now
            return False

    async def ask(self, model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 8192) -> str:
        if not self.api_key:
            raise ProviderError(self.name, "API key not configured")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        actual_model = _MODEL_MAP.get(model, model)
        payload = {
            "model": actual_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            data = await retry_ask(self.name, self._client, f"{self._base_url}/chat/completions", payload, headers)
        except Exception as e:
            raise ProviderError(self.name, str(e))
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response: {json.dumps(data, indent=2)[:300]}")
