# MCP Servers — Unified MCP Monorepo

[![CI](https://github.com/Medalcode/mcp-servers/actions/workflows/ci.yml/badge.svg)](https://github.com/Medalcode/mcp-servers/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Monorepo unificado con 6 servidores MCP (Model Context Protocol): Browser automation, AI Router, Web Scraping, Document Processing, LinkedIn, y Career Automation (Pathwise).

## Servers

| Server | Entry Point | Description |
|---|---|---|
| **BrowserMCP** | `servers.browser` | Automatización de navegador. Triple motor: Selenium, Playwright, estático |
| **RouteMCP** | `servers.route` | Router de IA multi-provider: Gemini, Groq, Cerebras con failover |
| **ScrapeMCP** | `servers.scrape` | Web scraping estructurado con protección SSRF |
| **DocMCP** | `servers.doc` | Manipulación de PDFs: leer, mergear, dividir, comprimir, generar |
| **LinkedInMCP** | `servers.linkedin` | Búsqueda y aplicación automatizada en LinkedIn |
| **Pathwise** | `servers.pathwise` | Plataforma de carrera con perfiles, CV, cover letters |

## Quick Start

```bash
# Instalar
pip install mcp-servers

# Ejecutar cualquier servidor
browsermcp    # Browser automation
routemcp      # AI Router
scrapemcp     # Web scraping
docmcp        # Document processing
linkedinmcp   # LinkedIn automation
pathwise      # Career platform
```

## Install from source

```bash
git clone https://github.com/Medalcode/mcp-servers.git
cd mcp-servers
pip install -e .
```

## Tech Stack

- **Python** — `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio JSON-RPC
- **Engines**: Selenium, Playwright, BeautifulSoup, httpx
- **AI Providers**: Google Gemini, Groq, Cerebras
- **PDF**: PyMuPDF, ReportLab, pypdf

## Project Structure

```
mcp-servers/
├── servers/           # Server entry points (browser, route, scrape, doc, linkedin, pathwise)
│   ├── browser.py
│   ├── route.py
│   ├── scrape.py
│   ├── doc.py
│   ├── linkedin.py
│   └── pathwise.py
├── engines/           # Browser engines (selenium, playwright, static)
├── router/            # AI Router engine + providers
├── scrapers/          # Web scrapers + exporters
├── docmcp/            # PDF processing
├── database/          # SQLite persistence
├── tools/             # MCP tool definitions
├── services/          # Business logic services
├── pyproject.toml
└── README.md
```

## License

MIT
