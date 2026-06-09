from mcp.server.fastmcp import FastMCP
from email_mcp.gmail import (
    search, read, send, draft, list_labels, list_threads,
)

mcp = FastMCP("EmailMCP")


@mcp.tool()
async def email_search(query: str, max_results: int = 10) -> str:
    return await search(query, max_results)


@mcp.tool()
async def email_read(email_id: str) -> str:
    return await read(email_id)


@mcp.tool()
async def email_send(to: str, subject: str, body: str, cc: str = "") -> str:
    return await send(to, subject, body, cc)


@mcp.tool()
async def email_draft(to: str, subject: str, body: str) -> str:
    return await draft(to, subject, body)


@mcp.tool()
async def email_labels() -> str:
    return await list_labels()


@mcp.tool()
async def email_threads(query: str = "", max_results: int = 10) -> str:
    return await list_threads(query, max_results)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
