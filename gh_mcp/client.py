import os
import json
from typing import Any

import httpx

GH_API = "https://api.github.com"


def _get_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    return {
        "Authorization": f"Bearer {token}" if token else "",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "medalcode-mcp-github",
    }


def _check_token():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    return bool(token)


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{GH_API}{path}", headers=_get_headers(), params=params, timeout=30)
        r.raise_for_status()
        return r.json()


async def _post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post(f"{GH_API}{path}", headers=_get_headers(), json=data, timeout=30)
        r.raise_for_status()
        return r.json()


async def _patch(path: str, data: dict) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.patch(f"{GH_API}{path}", headers=_get_headers(), json=data, timeout=30)
        r.raise_for_status()
        return r.json()


async def _put(path: str, data: dict | None = None) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.put(f"{GH_API}{path}", headers=_get_headers(), json=data, timeout=30)
        r.raise_for_status()
        return r.json()


async def get_repo(repo: str) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}")
        lines = [
            f"# {data['full_name']}",
            f"Description: {data.get('description', 'N/A')}",
            f"Stars: {data['stargazers_count']}  |  Forks: {data['forks_count']}  |  Issues: {data['open_issues_count']}",
            f"Language: {data.get('language', 'N/A')}",
            f"Default branch: {data['default_branch']}",
            f"Visibility: {data['visibility']}",
            f"Size: {data['size']} KB",
            f"Topics: {', '.join(data.get('topics', []))}",
            f"URL: {data['html_url']}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching repo: {e}"


async def list_issues(repo: str, state: str = "open", limit: int = 20) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/issues", {"state": state, "per_page": limit, "sort": "updated"})
        if not data:
            return f"No {state} issues found in {repo}"
        lines = [f"# Issues ({state}) — {repo}", ""]
        for issue in data:
            labels = ", ".join(lb["name"] for lb in issue.get("labels", []))
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"- #{issue['number']} {issue['title']}{label_str}")
            lines.append(f"  by {issue['user']['login']} — {issue['state']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing issues: {e}"


async def get_issue(repo: str, issue_number: int) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/issues/{issue_number}")
        labels = ", ".join(lb["name"] for lb in data.get("labels", []))
        lines = [
            f"# #{data['number']} {data['title']}",
            f"State: {data['state']}  |  Author: {data['user']['login']}",
            f"Labels: {labels or 'none'}",
            f"Created: {data['created_at'][:10]}  |  Updated: {data['updated_at'][:10]}",
            f"URL: {data['html_url']}",
            "",
            data.get('body', '(no description)')[:2000],
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching issue: {e}"


async def create_issue(repo: str, title: str, body: str = "", labels: str = "") -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data: dict[str, Any] = {"title": title, "body": body}
        if labels:
            data["labels"] = [lb.strip() for lb in labels.split(",")]
        result = await _post(f"/repos/{repo}/issues", data)
        return f"Created issue #{result['number']}: {result['html_url']}"
    except Exception as e:
        return f"Error creating issue: {e}"


async def close_issue(repo: str, issue_number: int) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        result = await _patch(f"/repos/{repo}/issues/{issue_number}", {"state": "closed"})
        return f"Closed issue #{result['number']}: {result['title']}"
    except Exception as e:
        return f"Error closing issue: {e}"


async def list_prs(repo: str, state: str = "open", limit: int = 20) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/pulls", {"state": state, "per_page": limit})
        if not data:
            return f"No {state} PRs found in {repo}"
        lines = [f"# Pull Requests ({state}) — {repo}", ""]
        for pr in data:
            lines.append(f"- !{pr['number']} {pr['title']}")
            lines.append(f"  by {pr['user']['login']} → {pr['base']['ref']} ({pr['state']})")
            if pr.get('draft'):
                lines[-1] += " [DRAFT]"
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing PRs: {e}"


async def get_pr(repo: str, pr_number: int) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/pulls/{pr_number}")
        lines = [
            f"# !{data['number']} {data['title']}",
            f"State: {data['state']}  |  Author: {data['user']['login']}",
            f"Base: {data['base']['ref']}  ←  Head: {data['head']['ref']}",
            f"Created: {data['created_at'][:10]}  |  Updated: {data['updated_at'][:10]}",
            f"URL: {data['html_url']}",
            "",
            data.get('body', '(no description)')[:2000],
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching PR: {e}"


async def merge_pr(repo: str, pr_number: int, commit_title: str = "") -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data: dict[str, Any] = {}
        if commit_title:
            data["commit_title"] = commit_title
        result = await _put(f"/repos/{repo}/pulls/{pr_number}/merge", data)
        if result.get("merged"):
            return f"Merged !{pr_number}: {result.get('message', '')}"
        return f"Merge failed: {result.get('message', 'unknown reason')}"
    except Exception as e:
        return f"Error merging PR: {e}"


async def list_branches(repo: str) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/branches", {"per_page": 50})
        lines = [f"# Branches — {repo}", ""]
        for branch in data:
            default = " [default]" if branch.get("name") in ("main", "master") else ""
            protected = " [protected]" if branch.get("protected") else ""
            lines.append(f"- {branch['name']}{default}{protected}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing branches: {e}"


async def list_workflows(repo: str) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/actions/workflows", {"per_page": 50})
        workflows = data.get("workflows", [])
        if not workflows:
            return f"No workflows found in {repo}"
        lines = [f"# Workflows — {repo}", ""]
        for wf in workflows:
            state = "✅" if wf["state"] == "active" else "❌"
            lines.append(f"- {state} {wf['name']} ({wf['path']})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing workflows: {e}"


async def trigger_workflow(repo: str, workflow_name: str, ref: str = "main", inputs: str = "") -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/actions/workflows", {"per_page": 50})
        workflows = data.get("workflows", [])
        wf = next((w for w in workflows if workflow_name in w["name"] or workflow_name in w["path"]), None)
        if not wf:
            available = ", ".join(w["name"] for w in workflows)
            return f"Workflow '{workflow_name}' not found. Available: {available}"
        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = json.loads(inputs)
        await _post(f"/repos/{repo}/actions/workflows/{wf['id']}/dispatches", payload)
        return f"Triggered workflow '{wf['name']}' on {ref}"
    except Exception as e:
        return f"Error triggering workflow: {e}"


async def list_commits(repo: str, branch: str = "main", limit: int = 10) -> str:
    if not _check_token():
        return "Error: GITHUB_TOKEN not configured"
    try:
        data = await _get(f"/repos/{repo}/commits", {"sha": branch, "per_page": limit})
        lines = [f"# Recent commits — {repo} ({branch})", ""]
        for commit in data:
            msg = commit["commit"]["message"].split("\n")[0][:80]
            author = commit["commit"]["author"]["name"]
            date = commit["commit"]["author"]["date"][:10]
            sha = commit["sha"][:7]
            lines.append(f"- {sha} {msg} ({author}, {date})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listing commits: {e}"
