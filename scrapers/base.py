import asyncio
import ipaddress
import logging
import os
import random
import re
import socket
import time
from dataclasses import dataclass

from urllib.parse import urlparse, unquote

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("scrapemcp.base")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_PRIVATE_BLOCKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

_BLOCKED_HOSTNAMES = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "metadata.google.internal", "169.254.169.254"}

_HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", "15"))

_BLOCKED_DOMAIN_PATTERNS = os.getenv(
    "BLOCKED_DOMAIN_PATTERNS",
    r"\.internal$|\.local$|\.localhost$|\.test$",
)


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed (only http/https)")
    hostname = parsed.hostname or ""
    hostname = unquote(hostname)

    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname}")

    if re.search(_BLOCKED_DOMAIN_PATTERNS, hostname.lower()):
        raise ValueError(f"Blocked domain: {hostname}")

    try:
        addrinfo = socket.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            addr = ipaddress.ip_address(ip_str)
            for block in _PRIVATE_BLOCKS:
                if addr in block:
                    raise ValueError(f"Blocked IP range: {ip_str}")
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {hostname}")


@dataclass
class ScrapeResult:
    url: str
    status: int
    data: dict | list | str | None = None
    error: str | None = None
    pages_scraped: int = 1


class BaseScraper:
    def __init__(self):
        self._session = httpx.AsyncClient(timeout=httpx.Timeout(_HTTP_TIMEOUT))
        self._session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
        })
        self._rate_limit = int(os.getenv("RATE_LIMIT_RPS", "5"))
        self._last_request = 0.0
        self._cache: dict[str, tuple[BeautifulSoup, str, float]] = {}
        self._cache_ttl = int(os.getenv("SCRAPE_CACHE_TTL", "300"))

    async def _rate_limit_wait(self):
        min_interval = 1.0 / self._rate_limit
        elapsed = time.monotonic() - self._last_request
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request = time.monotonic()

    async def _fetch(self, url: str) -> tuple[BeautifulSoup, str]:
        now = time.monotonic()
        if url in self._cache:
            soup, resolved_url, timestamp = self._cache[url]
            if now - timestamp < self._cache_ttl:
                logger.info("Cache hit: %s", url)
                return soup, resolved_url
            del self._cache[url]
        logger.info("Fetching URL: %s", url)
        _validate_url(url)
        await self._rate_limit_wait()
        self._session.headers["User-Agent"] = random.choice(USER_AGENTS)
        resp = await self._session.get(url, follow_redirects=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html5lib")
        resolved = str(resp.url)
        self._cache[url] = (soup, resolved, time.monotonic())
        return soup, resolved

    async def close(self):
        await self._session.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
