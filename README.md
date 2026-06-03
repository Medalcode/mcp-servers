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

## Quick Start

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
