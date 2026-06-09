from mcp.server.fastmcp import FastMCP
from gh_mcp.client import (
    get_repo, list_issues, get_issue, create_issue, close_issue,
    list_prs, get_pr, merge_pr, list_branches,
    list_workflows, trigger_workflow, list_commits,
)

mcp = FastMCP("GitHubMCP")


@mcp.tool()
async def repo_info(repo: str) -> str:
    return await get_repo(repo)


@mcp.tool()
async def issues(repo: str, state: str = "open", limit: int = 20) -> str:
    return await list_issues(repo, state, limit)


@mcp.tool()
async def issue_detail(repo: str, number: int) -> str:
    return await get_issue(repo, number)


@mcp.tool()
async def issue_create(repo: str, title: str, body: str = "", labels: str = "") -> str:
    return await create_issue(repo, title, body, labels)


@mcp.tool()
async def issue_close(repo: str, number: int) -> str:
    return await close_issue(repo, number)


@mcp.tool()
async def pull_requests(repo: str, state: str = "open", limit: int = 20) -> str:
    return await list_prs(repo, state, limit)


@mcp.tool()
async def pr_detail(repo: str, number: int) -> str:
    return await get_pr(repo, number)


@mcp.tool()
async def pr_merge(repo: str, number: int, commit_title: str = "") -> str:
    return await merge_pr(repo, number, commit_title)


@mcp.tool()
async def branches(repo: str) -> str:
    return await list_branches(repo)


@mcp.tool()
async def workflows(repo: str) -> str:
    return await list_workflows(repo)


@mcp.tool()
async def workflow_trigger(repo: str, workflow_name: str, ref: str = "main", inputs: str = "") -> str:
    return await trigger_workflow(repo, workflow_name, ref, inputs)


@mcp.tool()
async def commits(repo: str, branch: str = "main", limit: int = 10) -> str:
    return await list_commits(repo, branch, limit)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
