import os
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from task_tracker.engine import (
    create, list_tasks, update, complete, delete,
    add_dependency, remove_dependency, get_task, stats, brainstorm,
)

mcp = FastMCP("TaskTracker")


@mcp.tool()
async def task_create(title: str, priority: str = "medium", project: str = "",
                      deadline: str = "", tags: str = "", description: str = "") -> str:
    return create(title, priority, project, deadline, tags, description)


@mcp.tool()
async def task_list(status: str = "", project: str = "", priority: str = "") -> str:
    return list_tasks(status, project, priority)


@mcp.tool()
async def task_get(task_id: int) -> str:
    return get_task(task_id)


@mcp.tool()
async def task_update(task_id: int, title: str = "", priority: str = "",
                      status: str = "", project: str = "",
                      deadline: str = "", description: str = "") -> str:
    kwargs = {k: v for k, v in locals().items() if k != "task_id" and v}
    return update(task_id, **kwargs)


@mcp.tool()
async def task_complete(task_id: int) -> str:
    return complete(task_id)


@mcp.tool()
async def task_delete(task_id: int) -> str:
    return delete(task_id)


@mcp.tool()
async def task_depends(task_id: int, depends_on: int) -> str:
    return add_dependency(task_id, depends_on)


@mcp.tool()
async def task_undepends(task_id: int, depends_on: int) -> str:
    return remove_dependency(task_id, depends_on)


@mcp.tool()
async def task_stats() -> str:
    return stats()


@mcp.tool()
async def task_brainstorm(title: str, ideas: str) -> str:
    return brainstorm(title, ideas)


def main():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
