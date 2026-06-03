import atexit
import ipaddress
import logging
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


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "about"):
        raise ValueError(f"Scheme '{parsed.scheme}' not allowed (only http/https)")
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Blocked hostname: {hostname}")
    if re.search(r"\.internal$|\.local$|\.localhost$|\.test$", hostname.lower()):
        raise ValueError(f"Blocked domain: {hostname}")
    if hostname:
        try:
            addrinfo = socket.getaddrinfo(hostname, None)
            for _, _, _, _, sockaddr in addrinfo:
                ip_str = sockaddr[0]
                addr = ipaddress.ip_address(ip_str)
                for block in _PRIVATE_BLOCKS:
                    if addr in block:
                        raise ValueError(f"Blocked IP range: {ip_str}")
        except socket.gaierror:
            pass


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
        logger.warning("Screenshot too large (%d bytes), truncating", len(data))
        data = data[:max_bytes]
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


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
