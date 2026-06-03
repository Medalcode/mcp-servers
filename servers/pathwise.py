import logging
import sys
from mcp.server.fastmcp import FastMCP
from database import init_db
import tools.profile_tools
import tools.job_tools
import tools.application_tools
import tools.cover_letter_tools
import tools.cv_tools
import tools.auto_apply_tools
import tools.interview_tools

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("pathwise")

mcp = FastMCP("Pathwise")

init_db()

tools.profile_tools.register_tools(mcp)
tools.job_tools.register_tools(mcp)
tools.application_tools.register_tools(mcp)
tools.cover_letter_tools.register_tools(mcp)
tools.cv_tools.register_tools(mcp)
tools.auto_apply_tools.register_tools(mcp)
tools.interview_tools.register_tools(mcp)

logger.info("Pathwise MCP server initialized with 7 tool modules")

def main():
    import os
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
