# MCP Servers — Unified MCP Monorepo

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Monorepo unificado con 6 servidores MCP (Model Context Protocol).

## Servers

| Server | CLI | Description |
|---|---|---|
| **BrowserMCP** | `browsermcp` | Automatización de navegador con triple motor (Selenium, Playwright, estático) |
| **RouteMCP** | `routemcp` | Router de IA multi-provider (Gemini, Groq, Cerebras) con failover |
| **ScrapeMCP** | `scrapemcp` | Web scraping estructurado con protección SSRF |
| **DocMCP** | `docmcp` | Manipulación de PDFs: leer, mergear, dividir, comprimir, generar |
| **LinkedInMCP** | `linkedinmcp` | Búsqueda y aplicación en LinkedIn |
| **Pathwise** | `pathwise` | Plataforma de carrera con perfiles, CV, cover letters |
| **GitHub** | `python github_server.py` | API de GitHub: repos, issues, PRs |
| **Filesystem** | `python filesystem_server.py` | Operaciones de archivos locales |

## Install

```bash
pip install mcp-servers
```

## Quick Start (Docker)

Spin up all servers with a single command:

```bash
# 1. Copy and fill in your API keys
cp .env.example .env

# 2. Start everything
docker compose up --build
```

Each server exposes an SSE endpoint once running:

| Server | URL |
|---|---|
| BrowserMCP | `http://localhost:8001/sse` |
| RouteMCP | `http://localhost:8002/sse` |
| ScrapeMCP | `http://localhost:8003/sse` |
| DocMCP | `http://localhost:8004/sse` |
| LinkedInMCP | `http://localhost:8005/sse` |
| Pathwise | `http://localhost:8006/sse` |
| GitHub | `http://localhost:8007/sse` |
| Filesystem | `http://localhost:8008/sse` |

The `chromium` service (Selenium standalone Chrome) is shared by BrowserMCP and LinkedInMCP. A noVNC preview of the browser is available at `http://localhost:7900` (password: `secret`).

Files shared with `docmcp` and `filesystem` are mounted at `./workspace/`.

To run only specific servers:

```bash
docker compose up chromium browsermcp scrapemcp
```

## Quick Start (local)

```bash
# Todos los servidores se instalan como comandos CLI:
browsermcp      # Browser automation
routemcp        # AI Router
scrapemcp       # Web scraping
docmcp          # Document processing
linkedinmcp     # LinkedIn automation
pathwise        # Career platform

# GitHub y Filesystem se ejecutan directamente:
python github_server.py
python filesystem_server.py
```

## Tech Stack

- **Python** `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio JSON-RPC
- **Engines**: Selenium, Playwright, BeautifulSoup, httpx
- **AI Providers**: Google Gemini, Groq, Cerebras
- **PDF**: PyMuPDF, ReportLab, pypdf

## Project Structure

```
mcp-servers/
├── servers/            # Entry points (browser, route, scrape, doc, linkedin, pathwise)
├── engines/            # Browser engines
├── router/             # AI Router + providers
├── scrapers/           # Web scrapers
├── docmcp/             # PDF processing
├── database/           # SQLite persistence
├── tools/              # MCP tool definitions
├── services/           # Business logic
├── github_server.py    # GitHub API server
├── filesystem_server.py
└── pyproject.toml
```

## License

MIT
