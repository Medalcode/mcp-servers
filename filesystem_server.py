import os
import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("Filesystem MCP")

allowed = os.environ.get("ALLOWED_PATH")
if not allowed:
    raise RuntimeError("ALLOWED_PATH environment variable is required")
ALLOWED_PATH = Path(allowed).resolve()

MAX_READ_SIZE = 100 * 1024 * 1024
MAX_WRITE_SIZE = 10 * 1024 * 1024

logger.info("Filesystem MCP server starting, allowed path: %s", ALLOWED_PATH)


def _check_path(path: str) -> Path:
    full = (ALLOWED_PATH / path).resolve()
    resolved = str(full)
    allowed = str(ALLOWED_PATH)
    if not (resolved == allowed or resolved.startswith(allowed + "/")):
        raise ValueError(f"Path outside allowed directory: {path}")
    return full


@mcp.tool()
def read_file(path: str) -> str:
    logger.info("read_file called: %s", path)
    full = _check_path(path)
    if not full.is_file():
        return f"File not found: {path}"
    stat = full.stat()
    if stat.st_size > MAX_READ_SIZE:
        return f"File too large: {path} ({stat.st_size} bytes). Max: {MAX_READ_SIZE} bytes"
    return full.read_text(encoding="utf-8")


@mcp.tool()
def write_file(path: str, content: str) -> str:
    logger.info("write_file called: %s (%d chars)", path, len(content))
    full = _check_path(path)
    size = len(content.encode("utf-8"))
    if size > MAX_WRITE_SIZE:
        return f"Content too large: {size} bytes. Max: {MAX_WRITE_SIZE} bytes"
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return f"Written: {path}"


@mcp.tool()
def list_directory(path: str = "") -> str:
    logger.info("list_directory called: %s", path)
    full = _check_path(path)
    if not full.is_dir():
        return f"Directory not found: {path}"
    entries = []
    for entry in sorted(full.iterdir()):
        suffix = "/" if entry.is_dir() else ""
        entries.append(f"{entry.name}{suffix}")
    return "\n".join(entries)


@mcp.tool()
def file_info(path: str) -> str:
    logger.info("file_info called: %s", path)
    full = _check_path(path)
    if not full.exists():
        return f"Not found: {path}"
    stat = full.stat()
    return (
        f"Path: {full}\n"
        f"Type: {'directory' if full.is_dir() else 'file'}\n"
        f"Size: {stat.st_size} bytes\n"
        f"Modified: {stat.st_mtime}"
    )


@mcp.tool()
def search_files(pattern: str, path: str = "") -> str:
    logger.info("search_files called: pattern=%s path=%s", pattern, path)
    full = _check_path(path)
    matches = sorted(full.rglob(pattern))
    max_depth = 5
    result = []
    for m in matches:
        rel = m.relative_to(ALLOWED_PATH)
        depth = len(rel.parts)
        if depth <= max_depth:
            result.append(str(rel))
    return "\n".join(result) or "No matches"


@mcp.tool()
def delete_file(path: str) -> str:
    logger.info("delete_file called: %s", path)
    full = _check_path(path)
    if not full.exists():
        return f"Not found: {path}"
    if full.is_file():
        full.unlink()
        return f"Deleted: {path}"
    if full.is_dir():
        try:
            full.rmdir()
            return f"Deleted: {path}"
        except OSError as e:
            return f"Cannot delete directory: {path} - {e}"
    return f"Cannot delete: {path} is not a regular file or directory"


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")
