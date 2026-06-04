# MCP Servers — Unified MCP Monorepo

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/medalcode-mcp-servers)](https://pypi.org/project/medalcode-mcp-servers/)

Monorepo unificado con 6 servidores MCP (Model Context Protocol) para automatización de búsqueda y postulación de empleo.

## Servers

| Server | CLI | Description |
|---|---|---|
| **BrowserMCP** | `browsermcp` | Automatización de navegador con Selenium |
| **RouteMCP** | `routemcp` | Router de IA multi-provider (Gemini, Groq, Cerebras) con failover |
| **ScrapeMCP** | `scrapemcp` | Web scraping estructurado con protección SSRF |
| **DocMCP** | `docmcp` | Manipulación de PDFs: leer, mergear, dividir, comprimir, generar |
| **LinkedInMCP** | `linkedinmcp` | Búsqueda y postulación automática en LinkedIn |
| **Pathwise** | `pathwise` | Pipeline completo: perfiles, CV, cover letters, postulación |

## Install

```bash
pip install medalcode-mcp-servers
```

O desde el repo:

```bash
git clone https://github.com/Medalcode/mcp-servers.git
cd mcp-servers
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick Start

Configurar credenciales vía variables de entorno, luego:

```bash
browsermcp      # Browser automation
routemcp        # AI Router
scrapemcp       # Web scraping
docmcp          # Document processing
linkedinmcp     # LinkedIn automation
pathwise        # Career platform
```

## Seguridad

- **bcrypt** para passwords de administrador (fallback SHA-256 si no disponible)
- **DNS rebinding prevention**: re-validación de IP post-redirect
- **run_script sandbox**: bloquea fetch/XHR/WebSocket en scripts inyectados
- **Path traversal protegido**: todos los servers validan rutas contra directorios permitidos
- **SQL injection prevenido**: parámetros parametrizados + CHECK constraints
- **Atomic writes**: credenciales escritas via tempfile + rename
- **Rate limiting**: detección y backoff automático en LinkedIn

## Estructura

```
servers/            → 6 entry points MCP
engines/            → SeleniumEngine, StaticEngine
router/             → RouteMCP providers (Google, Groq, Cerebras)
scrapers/           → ScrapeMCP (page, list, table, sitemap)
docmcp/             → DocMCP (reader, manipulator, generator)
services/           → Pathwise (AI, CV, forms, jobs, scrapers)
tools/              → Pathwise tools (profile, job, application, CV, auto-apply)
database/           → SQLite + repositorios, bcrypt auth
```

## Tech Stack

- **Python** `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio JSON-RPC
- **Engine**: Selenium, BeautifulSoup + lxml, httpx
- **AI Providers**: Google Gemini, Groq, Cerebras
- **PDF**: PyMuPDF, ReportLab, pypdf

## License

MIT
