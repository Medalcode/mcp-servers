from mcp.server.fastmcp import FastMCP
from memory_engine.store import (
    remember, recall, search, forget, list_by_category,
    save_context, get_context, stats, get_categories,
)

mcp = FastMCP("MemoryMCP")


@mcp.tool()
async def remember_value(key: str, value: str, category: str = "general", tags: str = "") -> str:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    return remember(key, value, category, tag_list)


@mcp.tool()
async def recall_value(key: str) -> str:
    return recall(key)


@mcp.tool()
async def search_memory(query: str, category: str = "") -> str:
    return search(query, category)


@mcp.tool()
async def forget_value(key: str) -> str:
    return forget(key)


@mcp.tool()
async def list_memories(category: str = "") -> str:
    return list_by_category(category)


@mcp.tool()
async def memory_stats() -> str:
    return stats()


@mcp.tool()
async def categories() -> str:
    cats = get_categories()
    if not cats:
        return "No categories yet"
    return "Categories:\n" + "\n".join(f"- {c}" for c in cats)


@mcp.tool()
async def save_session_context(session_id: str, content: str) -> str:
    return save_context(session_id, content)


@mcp.tool()
async def get_session_context(session_id: str, limit: int = 10) -> str:
    return get_context(session_id, limit)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
