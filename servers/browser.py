import atexit
import ipaddress
import logging
import sys
import os
import base64
import re
import socket
import threading
from urllib.parse import urlparse
from mcp.server.fastmcp import FastMCP

from engines.static import StaticEngine
from engines.playwright_engine import PlaywrightEngine
from engines.selenium_engine import SeleniumEngine

logger = logging.getLogger(__name__)

mcp = FastMCP("Browser MCP")

_engine = None
_engine_lock = threading.Lock()


def _ensure_engine():
    global _engine
    if _engine is not None:
        return _engine
    with _engine_lock:
        if _engine is not None:
            return _engine
        engine_mode = os.environ.get("BROWSER_ENGINE", "auto")
        if engine_mode == "playwright":
            _engine = PlaywrightEngine()
            return _engine
        if engine_mode == "static":
            _engine = StaticEngine()
            return _engine
        if engine_mode == "selenium":
            _engine = SeleniumEngine()
            return _engine
        try:
            _engine = SeleniumEngine()
            result = _engine.navigate("about:blank")
            if result.error:
                logger.warning("Selenium engine failed (%s), falling back to static engine", result.error)
                _engine = StaticEngine()
            return _engine
        except Exception as exc:
            logger.warning("Selenium engine raised %s, falling back to static engine", exc)
            _engine = StaticEngine()
            return _engine


def _close_engine():
    global _engine
    if _engine is not None:
        try:
            _engine.close()
        except Exception:
            logger.exception("engine close failed")


def get_engine():
    return _ensure_engine()


atexit.register(_close_engine)

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

# Cache DNS lookups to reduce latency and mitigate some SSRF attacks
_dns_cache: dict[str, bool] = {}
_dns_cache_ttl = 300


def _is_private_hostname(hostname: str) -> bool:
    if not hostname:
        return False
    cache_key = hostname.lower()
    cached = _dns_cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(5)
        try:
            addrinfo = socket.getaddrinfo(hostname, None)
        finally:
            socket.setdefaulttimeout(old_timeout)
        for _, _, _, _, sockaddr in addrinfo:
            ip_str = sockaddr[0]
            addr = ipaddress.ip_address(ip_str)
            for block in _PRIVATE_BLOCKS:
                if addr in block:
                    _dns_cache[cache_key] = True
                    return True
    except (socket.gaierror, OSError):
        pass
    _dns_cache[cache_key] = False
    return False


def _dns_resolves(hostname: str) -> bool:
    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except socket.gaierror:
        return False


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed (only http/https)")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials not allowed (user:password@host)")
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname}")
    if re.search(r"\.internal$|\.local$|\.localhost$|\.test$", hostname.lower()):
        raise ValueError(f"Blocked domain: {hostname}")
    if hostname and _is_private_hostname(hostname):
        raise ValueError(f"Blocked private IP range for hostname: {hostname}")

    # Reject URLs with bare IP addresses in private ranges (bypass DNS)
    try:
        addr = ipaddress.ip_address(hostname)
        for block in _PRIVATE_BLOCKS:
            if addr in block:
                raise ValueError(f"Blocked private IP: {hostname}")
    except ValueError:
        if not _dns_resolves(hostname):
            raise ValueError(f"Hostname does not resolve: {hostname}")


def _validate_final_url(result) -> str | None:
    if not result or not result.url:
        return None
    parsed = urlparse(result.url)
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return f"Navigation redirected to blocked hostname: {hostname}"
    if hostname and _is_private_hostname(hostname):
        return f"Navigation redirected to private IP: {hostname}"
    return None


_BLOCKED_JS_PATTERNS = [
    r"\bfetch\s*\(",
    r"\bxmlhttprequest\b",
    r"\bwebsocket\b",
    r"\bfilereader\b",
    r"\bimportscripts\b",
    r"\bworker\b",
    r"\bnavigator\.sendbeacon\b",
    r"\bdocument\.write\b",
    r"\bdocument\.open\b",
    r"\btop\.",
    r"\bparent\.",
    r"\b(alert|confirm|prompt)\s*\(",
]


def _validate_script(script: str) -> None:
    # Deny-by-default: only allow simple DOM read/write scripts
    dangerous = [
        "eval", "function", "settimeout", "setinterval",
        "new function", "reflect.construct",
        "import(", "importscripts",
    ]
    script_lower = script.lower()
    for keyword in dangerous:
        if keyword in script_lower:
            raise ValueError(f"Script blocked: contains dangerous API '{keyword}'")
    for pattern in _BLOCKED_JS_PATTERNS:
        if re.search(pattern, script_lower):
            raise ValueError("Script blocked: contains dangerous API")


def _engine_prefix(engine) -> str:
    return f"[Engine: {engine.name}] "


@mcp.tool()
def navigate(url: str) -> str:
    try:
        _validate_url(url)
    except ValueError as e:
        return f"URL validation error: {e}"
    engine = get_engine()
    result = engine.navigate(url)
    if result.error:
        return f"{_engine_prefix(engine)}Error: {result.error}"
    redirect_error = _validate_final_url(result)
    if redirect_error:
        return f"{_engine_prefix(engine)}{redirect_error}"
    return (
        f"{_engine_prefix(engine)}Title: {result.title}\n"
        f"URL: {result.url}\n"
        f"---\n"
        f"{result.text}"
    )


@mcp.tool()
def extract(selector: str) -> str:
    engine = get_engine()
    results = engine.extract(selector)
    if not results:
        return f"{_engine_prefix(engine)}No elements matched"
    return f"{_engine_prefix(engine)}\n---\n".join(results)


@mcp.tool()
def links() -> str:
    engine = get_engine()
    links = engine.get_links()
    if not links:
        return f"{_engine_prefix(engine)}No links found"
    lines = [f"{_engine_prefix(engine)}"]
    for i, link in enumerate(links, 1):
        icon = "🔗" if link.is_internal else "🌐"
        lines.append(f"{i}. {icon} {link.text or '(no text)'}")
        lines.append(f"   {link.href}")
    return "\n".join(lines)


@mcp.tool()
def forms() -> str:
    engine = get_engine()
    forms_list = engine.get_forms()
    if not forms_list:
        return f"{_engine_prefix(engine)}No forms found"
    output = [f"{_engine_prefix(engine)}"]
    for i, form in enumerate(forms_list, 1):
        output.append(f"Form #{i}: {form.method} -> {form.action}")
        for field in form.fields:
            req = " *" if field.required else ""
            output.append(f"  [{field.tag}] {field.name} ({field.type}){req}")
            if field.label:
                output.append(f"       Label: {field.label}")
    return "\n".join(output)


@mcp.tool()
def screenshot() -> str:
    engine = get_engine()
    data = engine.screenshot()
    if data is None:
        return f"{_engine_prefix(engine)}Screenshot not available with current engine"
    max_bytes = int(os.environ.get("BROWSER_SCREENSHOT_MAX_BYTES", "5242880"))
    if len(data) > max_bytes:
        logger.warning("Screenshot too large (%d bytes), resizing not supported, returning error", len(data))
        return f"{_engine_prefix(engine)}Screenshot too large ({len(data)} bytes, max {max_bytes})"
    b64 = base64.b64encode(data).decode()
    return f"data:image/png;base64,{b64}"


@mcp.tool()
def click(selector: str) -> str:
    engine = get_engine()
    result = engine.click(selector)
    return f"{_engine_prefix(engine)}{result}"


@mcp.tool()
def click_by_text(text: str) -> str:
    engine = get_engine()
    result = engine.click_by_text(text)
    return f"{_engine_prefix(engine)}{result}"


@mcp.tool()
def run_script(script: str) -> str:
    try:
        _validate_script(script)
    except ValueError as e:
        return f"{_engine_prefix(_ensure_engine())}Script blocked: {e}"
    engine = get_engine()
    result = engine.run_script(script)
    return f"{_engine_prefix(engine)}{result}"


@mcp.tool()
def fill(selector: str, value: str) -> str:
    engine = get_engine()
    return f"{_engine_prefix(engine)}{engine.fill(selector, value)}"


@mcp.tool()
def scroll(direction: str = "down") -> str:
    engine = get_engine()
    return f"{_engine_prefix(engine)}{engine.scroll(direction)}"


@mcp.tool()
def wait(ms: int = 1000) -> str:
    engine = get_engine()
    return f"{_engine_prefix(engine)}{engine.wait(ms)}"


@mcp.tool()
def engine_info() -> str:
    engine = get_engine()
    return f"Active engine: {engine.name}"


from servers.server_base import run_server


def main():
    run_server(mcp, use_sse=True, setup_logging=True)


if __name__ == "__main__":
    main()
