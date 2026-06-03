import json
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from docmcp.reader import PDFReader
from docmcp.manipulator import PDFManipulator
from docmcp.generator import PDFGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docmcp")

mcp = FastMCP("DocMCP")
reader = PDFReader()
manip = PDFManipulator()
gen = PDFGenerator()
workdir = os.environ.get("DOCMCP_WORKDIR", os.path.expanduser("~"))


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


@mcp.tool()
def read(path: str) -> str:
    try:
        data = reader.read(_resolve(path))
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    text = data["text"][:5000]
    result = f"""File: {data['file']}
Pages: {data['pages']}
Metadata: {json.dumps(data['metadata'], indent=2)}
---Content (first 5000 chars)---
{text}"""
    return result


@mcp.tool()
def info(path: str) -> str:
    try:
        data = reader.info(_resolve(path))
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    return json.dumps(data, indent=2)


@mcp.tool()
def extract_images(path: str, output_dir: str = "") -> str:
    try:
        resolved_out = _resolve(output_dir) if output_dir else ""
        data = reader.extract_images(_resolve(path), resolved_out)
    except ValueError as e:
        return str(e)
    if "error" in data:
        return data["error"]
    return json.dumps(data, indent=2)


@mcp.tool()
def to_markdown(path: str, output: str = "") -> str:
    try:
        data = reader.to_markdown(_resolve(path))
        if output:
            out_path = _resolve(output)
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
        resolved_paths = [_resolve(p) for p in path_list]
        resolved_out = _resolve(output)
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
        result = manip.split(_resolve(path), resolved_out)
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def extract_pages(path: str, pages: str, output: str) -> str:
    try:
        result = manip.extract_pages(_resolve(path), pages, _resolve(output))
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def compress(path: str, output: str) -> str:
    try:
        result = manip.compress(_resolve(path), _resolve(output))
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_report(title: str, content: str, output: str) -> str:
    try:
        result = gen.report(title, content, _resolve(output))
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
        gen.table_report(title, header_list, row_data, _resolve(output))
        return f"Generated: {output}"
    except ValueError as e:
        return str(e)


@mcp.tool()
def generate_text(text: str, output: str, title: str = "") -> str:
    try:
        result = gen.text_to_pdf(text, _resolve(output), title)
    except ValueError as e:
        return str(e)
    if "error" in result:
        return result["error"]
    return json.dumps(result, indent=2)


def main():
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
