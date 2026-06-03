import json
import logging
import os
import time

import httpx

from .base import AIProvider, ProviderError, retry_ask

logger = logging.getLogger(__name__)


class GoogleProvider(AIProvider):
    name = "google"
    _CACHE_TTL = 60

    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        self._available_cache: bool | None = None
        self._available_cache_time: float = 0.0

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        now = time.monotonic()
        if self._available_cache is not None and now - self._available_cache_time < self._CACHE_TTL:
            return self._available_cache
        try:
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            resp = await self._client.get(url, headers={"X-Goog-Api-Key": self.api_key})
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        headers = {"X-Goog-Api-Key": self.api_key}
        try:
            data = await retry_ask(self.name, self._client, url, payload, headers)
        except Exception as e:
            raise ProviderError(self.name, str(e))
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ProviderError(self.name, f"Unexpected response: {json.dumps(data, indent=2)[:300]}")
