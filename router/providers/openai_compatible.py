import json
import logging
import os
import time

import httpx

from .base import AIProvider, ProviderError, retry_ask

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    name = "openai_compatible"
    _CACHE_TTL = 60

    def __init__(self, name: str, api_key_env: str, base_url: str, model_map: dict[str, str]):
        self.name = name
        self._api_key_env = api_key_env
        self.api_key = os.environ.get(api_key_env, "")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._base_url = base_url.rstrip("/")
        self._model_map = model_map
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
            raise ProviderError(self.name, f"{self._api_key_env} not configured")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        actual_model = self._model_map.get(model, model)
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
        except (KeyError, IndexError):
            raise ProviderError(self.name, f"Unexpected response: {json.dumps(data, indent=2)[:300]}")
