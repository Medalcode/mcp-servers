import json
import logging
import time

import httpx

from .base import AIProvider, ProviderError, retry_ask

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    name = "ollama"
    _CACHE_TTL = 60

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._base_url = "http://localhost:11434/api"
        self._available_cache: bool | None = None
        self._available_cache_time: float = 0.0

    async def is_available(self) -> bool:
        now = time.monotonic()
        if self._available_cache is not None and now - self._available_cache_time < self._CACHE_TTL:
            return self._available_cache
        try:
            resp = await self._client.get("http://localhost:11434/")
            self._available_cache = resp.status_code == 200
            self._available_cache_time = now
            return self._available_cache
        except Exception:
            logger.exception("%s availability check failed", self.name)
            self._available_cache = False
            self._available_cache_time = now
            return False

    async def ask(self, model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 8192) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        try:
            data = await retry_ask(self.name, self._client, f"{self._base_url}/generate", payload, headers)
        except Exception as e:
            raise ProviderError(self.name, str(e))
        try:
            return data["response"]
        except (KeyError, TypeError):
            raise ProviderError(self.name, f"Unexpected response: {json.dumps(data, indent=2)[:300]}")
