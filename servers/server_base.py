import os
import sys
import logging

from dotenv import load_dotenv


def run_server(mcp, *, use_sse=False, setup_logging=False, env_path=None):
    if setup_logging:
        logging.basicConfig(
            stream=sys.stderr,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%H:%M:%S",
        )

    if env_path is None:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)

    if use_sse:
        transport = os.environ.get("MCP_TRANSPORT", "stdio")
        if transport == "sse":
            mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"),
                    port=int(os.environ.get("MCP_PORT", "8080")))
            return

    mcp.run(transport="stdio")
