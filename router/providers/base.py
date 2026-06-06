import asyncio
from abc import ABC, abstractmethod


import httpx


class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def ask(self, model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 8192) -> str: ...

    @abstractmethod
    async def is_available(self) -> bool: ...


class ProviderError(Exception):
    def __init__(self, provider: str, message: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")


_RETRY_DELAYS = [1, 2, 4, 8, 16]
_MAX_RETRIES = 5


async def retry_ask(provider_name: str, client: httpx.AsyncClient, url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    for attempt in range(_MAX_RETRIES):
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                raw = resp.headers.get("Retry-After", str(_RETRY_DELAYS[attempt]))
                try:
                    retry_after = int(raw)
                except ValueError:
                    retry_after = _RETRY_DELAYS[attempt]
                await asyncio.sleep(retry_after)
                continue
            resp.raise_for_status()
            return resp.json()
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            if attempt == _MAX_RETRIES - 1:
                raise
            await asyncio.sleep(_RETRY_DELAYS[attempt])
    raise RuntimeError(f"{provider_name}: max retries exceeded")
