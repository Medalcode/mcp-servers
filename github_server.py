import logging
import sys
import os
from functools import wraps

import github
from github import Github, Auth
from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP("GitHub MCP")

token = os.environ.get("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN environment variable required")

gh = Github(auth=Auth.Token(token))

try:
    user = gh.get_user()
    logger.info("Token validated - logged in as %s", user.login)
except github.BadCredentialsException as e:
    raise RuntimeError(f"GITHUB_TOKEN is invalid or expired: {e}")
except Exception as e:
    raise RuntimeError(f"Failed to validate GitHub token: {e}")


def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info("Calling %s(args=%s, kwargs=%s)", func.__name__, args[1:] if args else "?", kwargs)
        try:
            return func(*args, **kwargs)
        except github.RateLimitExceededException as e:
            return f"GitHub API rate limit exceeded: {e}"
        except github.GithubException as e:
            return f"GitHub API error: {e}"
        except ValueError as e:
            return f"Validation error: {e}"
    return wrapper


def _paginate(queriable, limit: int, start_page: int = 0):
    items = []
    page = start_page
    while len(items) < limit:
        batch = queriable.get_page(page)
        if not batch:
            break
        items.extend(batch)
        page += 1
    return items[:limit]


def validate_repo(repo: str) -> None:
    if not repo or repo.startswith("/") or repo.endswith("/"):
        raise ValueError("Invalid repository format: must be 'owner/repo' with no leading/trailing slashes")
    if repo.count("/") != 1:
        raise ValueError("Invalid repository format: must be 'owner/repo' (exactly one '/')")


@mcp.tool()
@handle_errors
def search_repositories(query: str, limit: int = 10) -> str:
    limit = min(limit, 200)
    repos = _paginate(gh.search_repositories(query), limit)
    return "\n".join(f"{r.full_name} - {r.stargazers_count} stars - {r.description or ''}" for r in repos)


@mcp.tool()
@handle_errors
def get_repository(repo: str) -> str:
    validate_repo(repo)
    r = gh.get_repo(repo)
    return (
        f"Name: {r.full_name}\n"
        f"Description: {r.description or ''}\n"
        f"Stars: {r.stargazers_count}\n"
        f"Forks: {r.forks_count}\n"
        f"Language: {r.language}\n"
        f"Topics: {', '.join(r.get_topics())}\n"
        f"URL: {r.html_url}"
    )


@mcp.tool()
@handle_errors
def list_issues(repo: str, state: str = "open", limit: int = 10) -> str:
    limit = min(limit, 200)
    r = gh.get_repo(repo)
    issues = _paginate(r.get_issues(state=state), limit)
    return "\n".join(f"#{i.number} {i.title} ({i.state}) - {i.html_url}" for i in issues)


@mcp.tool()
@handle_errors
def get_file_content(repo: str, path: str, ref: str = "main") -> str:
    r = gh.get_repo(repo)
    content = r.get_contents(path, ref=ref)
    if isinstance(content, list):
        return "\n".join(c.path for c in content)
    try:
        return content.decoded_content.decode("utf-8")
    except UnicodeDecodeError:
        return "Binary file, cannot display as text"


@mcp.tool()
@handle_errors
def list_branches(repo: str) -> str:
    r = gh.get_repo(repo)
    return "\n".join(b.name for b in r.get_branches())


@mcp.tool()
@handle_errors
def create_issue(repo: str, title: str, body: str = "") -> str:
    r = gh.get_repo(repo)
    issue = r.create_issue(title=title, body=body)
    return f"Issue #{issue.number} created: {issue.html_url}"


@mcp.tool()
@handle_errors
def list_pull_requests(repo: str, state: str = "open", limit: int = 10) -> str:
    limit = min(limit, 200)
    r = gh.get_repo(repo)
    prs = _paginate(r.get_pulls(state=state), limit)
    return "\n".join(f"#{pr.number} {pr.title} ({pr.state}) - {pr.html_url}" for pr in prs)


@mcp.tool()
@handle_errors
def list_recent_commits(repo: str, branch: str = "main", limit: int = 10) -> str:
    limit = min(limit, 200)
    r = gh.get_repo(repo)
    commits = _paginate(r.get_commits(sha=branch), limit)
    return "\n".join(
        f"{c.sha[:8]} {c.commit.message.split("\n")[0]} - {c.commit.author.name}" for c in commits
    )


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")
