# MCP Servers — GitHub + Filesystem

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Two lightweight MCP servers for GitHub API access and local filesystem operations.

## Servers

### GitHub Server (`github_server.py`)

Provides GitHub API tools: search repos, get repo details, list issues, read files, create issues, list PRs, list commits.

**Required env var:** `GITHUB_TOKEN`

### Filesystem Server (`filesystem_server.py`)

Provides filesystem tools: read, write, list directory, file info, search files, delete.

**Required env var:** `ALLOWED_PATH` — root directory to restrict access to (no default for security)

## Quick Start

```bash
# GitHub server
export GITHUB_TOKEN="ghp_..."
python github_server.py

# Filesystem server
export ALLOWED_PATH=/home/user/allowed
python filesystem_server.py
```

## Tech Stack

- **Python** — `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio
- **GitHub**: `PyGithub`
- **Filesystem**: `pathlib` (stdlib)

## 🔧 Recent Improvements

- **Path Traversal Fixed** — `filesystem_server.py`: trailing-slash prefix check prevents bypasses
- **`ALLOWED_PATH` Now Required** — No default (was `/home/medalcode`), must be explicitly set
- **Size Limits** — Read: 100MB max, Write: 10MB max
- **`delete_file` Error Handling** — Handles non-empty directories, false-positive messages fixed
- **GitHub Error Handling** — All tools wrapped in try/except; rate limits and network errors caught
- **Binary File Support** — `get_file_content` gracefully handles non-UTF-8 content
- **`limit` Bounded** — All list tools enforce max 100 results
- **Token Validation** — GitHub token verified at startup
- **Logging** — All tool calls logged at INFO level
- **`search_files` Max Depth** — Prevents deep recursion with `max_depth=5`
