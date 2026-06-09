import json
import logging
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from docmcp.reader import PDFReader
from docmcp.manipulator import PDFManipulator
from docmcp.generator import PDFGenerator

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("docmcp")

mcp = FastMCP("DocMCP")
reader = PDFReader()
manip = PDFManipulator()
gen = PDFGenerator()
workdir = os.environ.get("DOCMCP_WORKDIR", os.path.expanduser("~"))
MAX_DOC_SIZE_MB = int(os.environ.get("DOCMCP_MAX_SIZE_MB", "200"))


def _resolve(path: str) -> str:
    user_path = Path(path)
    if not user_path.is_absolute():
        user_path = Path(workdir) / user_path
    full = user_path.resolve()
    allowed = Path(workdir).resolve()
    allowed_str = str(allowed)
    full_str = str(full)
    if not (full_str == allowed_str or full_str.startswith(allowed_str + "/")):
        raise ValueError(f"Path not allowed: {path}")
    return str(full)


def _validate_doc_path(path: str) -> str:
    resolved = _resolve(path)
    if not os.path.isfile(resolved):
        raise ValueError(f"File not found: {path}")
    size_mb = os.path.getsize(resolved) / (1024 * 1024)
    if size_mb > MAX_DOC_SIZE_MB:
        raise ValueError(f"File too large: {size_mb:.0f}MB (max {MAX_DOC_SIZE_MB}MB)")
    return resolved


def _safe_resolve_output(output: str) -> str:
    out = _resolve(output)
    parent = Path(out).parent
    parent.mkdir(parents=True, exist_ok=True)
    return out


@mcp.tool()
def read(path: str, max_chars: int = 5000) -> str:
    try:
        data = reader.read(_validate_doc_path(path))
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    snippet = data["text"][:max_chars] if max_chars else data["text"]
    truncated = ""
    if max_chars and len(data["text"]) > max_chars:
        truncated = f"\n[Truncated: showing {max_chars} of {len(data['text'])} chars]"
    result = f"""File: {data['file']}
Pages: {data['pages']}
Metadata: {json.dumps(data['metadata'], indent=2)}
---Content{truncated}---
{snippet}"""
    return result


@mcp.tool()
def info(path: str) -> str:
    try:
        data = reader.info(_validate_doc_path(path))
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    return json.dumps(data, indent=2)


@mcp.tool()
def extract_images(path: str, output_dir: str = "") -> str:
    try:
        resolved_out = _resolve(output_dir) if output_dir else ""
        data = reader.extract_images(_validate_doc_path(path), resolved_out)
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    return json.dumps(data, indent=2)


@mcp.tool()
def to_markdown(path: str, output: str = "") -> str:
    try:
        data = reader.to_markdown(_validate_doc_path(path))
        if output:
            out_path = _safe_resolve_output(output)
            Path(out_path).write_text(data, encoding="utf-8")
            return f"Converted to {output}"
        return data
    except ValueError as e:
        return str(e)


@mcp.tool()
def merge(paths: str, output: str) -> str:
    try:
        if "\n" in paths:
            path_list = [p.strip() for p in paths.split("\n") if p.strip()]
        else:
            path_list = [p.strip() for p in paths.split(",")]
        resolved_paths = [_validate_doc_path(p) for p in path_list]
        resolved_out = _safe_resolve_output(output)
    except ValueError as e:
        return str(e)
    result = manip.merge(resolved_paths, resolved_out)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def split(path: str, output_dir: str = "") -> str:
    try:
        resolved_out = _resolve(output_dir) if output_dir else ""
        result = manip.split(_validate_doc_path(path), resolved_out)
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def extract_pages(path: str, pages: str, output: str) -> str:
    try:
        result = manip.extract_pages(_validate_doc_path(path), pages, _safe_resolve_output(output))
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def compress(path: str, output: str) -> str:
    try:
        result = manip.compress(_validate_doc_path(path), _safe_resolve_output(output))
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_report(title: str, content: str, output: str) -> str:
    try:
        result = gen.report(title, content, _safe_resolve_output(output))
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_table(title: str, headers: str, rows: str, output: str) -> str:
    try:
        header_list = [h.strip() for h in headers.split(",")]
        try:
            row_data = json.loads(rows)
        except json.JSONDecodeError as e:
            return f"Invalid JSON for rows: {e}"
        if not isinstance(row_data, list):
            return "Error: rows must be a JSON array"
        for item in row_data:
            if not isinstance(item, (list, dict)):
                return "Error: each row must be a JSON object or array"
        gen.table_report(title, header_list, row_data, _safe_resolve_output(output))
        return f"Generated: {output}"
    except ValueError as e:
        return str(e)


@mcp.tool()
def generate_text(text: str, output: str, title: str = "") -> str:
    try:
        result = gen.text_to_pdf(text, _safe_resolve_output(output), title)
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


def main():
    load_dotenv()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
