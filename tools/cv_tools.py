from mcp.server import FastMCP
from services.cv_service import parse_pdf, parse_cv_text
from services.ai_provider import parse_cv_with_ai

def register_tools(mcp: FastMCP):
    @mcp.tool()
    async def cv_parse_pdf(file_path: str, use_ai: bool = False) -> str:
        """Extract structured data from a PDF CV file. Set use_ai=true for AI-powered extraction (better but slower), or false for regex-based extraction (faster)."""
        import os
        from pathlib import Path
        
        allowed_dir = os.environ.get("CV_ALLOWED_PATH", os.path.expanduser("~"))
        full = Path(file_path).resolve()
        allowed = Path(allowed_dir).resolve()
        if not (str(full) == str(allowed) or str(full).startswith(str(allowed) + os.sep)):
            return "Error: Path not allowed"
            
        result = await parse_pdf(file_path)
        text = result["text"]

        if use_ai:
            parsed = await parse_cv_with_ai(text)
        else:
            parsed = parse_cv_text(text)

        import json
        return json.dumps({
            "pages": result["pages"],
            "method": "AI" if use_ai else "regex",
            "data": parsed,
        }, indent=2, ensure_ascii=False)
