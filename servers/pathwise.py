import logging
import os
import sys
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
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

from servers.server_base import run_server


def main():
    run_server(mcp, use_sse=True)


if __name__ == "__main__":
    main()
