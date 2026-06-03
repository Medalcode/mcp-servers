# MCP Servers — Unified MCP Monorepo

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-113%20passing-brightgreen.svg)]()

Monorepo unificado con 6 servidores MCP (Model Context Protocol) + herramientas de carrera Pathwise.

## Servers

| Server | CLI | Description |
|---|---|---|
| **BrowserMCP** | `browsermcp` | Automatización de navegador con triple motor (Selenium, Playwright, estático) |
| **RouteMCP** | `routemcp` | Router de IA multi-provider (Gemini, Groq, Cerebras) con failover |
| **ScrapeMCP** | `scrapemcp` | Web scraping estructurado con protección SSRF + caché |
| **DocMCP** | `docmcp` | Manipulación de PDFs: leer, mergear, dividir, comprimir, generar |
| **LinkedInMCP** | `linkedinmcp` | Búsqueda y aplicación en LinkedIn (solo env vars, sin credenciales en disco) |
| **Pathwise** | `pathwise` | Plataforma de carrera: perfiles, CV, cover letters, auto-apply |
| **GitHub** | `python github_server.py` | API de GitHub: repos, issues, PRs (con paginación hasta 200) |
| **Filesystem** | `python filesystem_server.py` | Operaciones de archivos locales con chunked reading |

## Install

```bash
pip install medalcode-mcp-servers
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

1. Copia el archivo de ejemplo para configurar tus variables de entorno:
```bash
cp .env.example .env
```
2. Edita el archivo `.env` con tus credenciales.
3. Ejecuta los servidores:

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

## Seguridad

- **bcrypt** para passwords de administrador (fallback SHA-256 si no disponible)
- **DNS rebinding prevention**: re-validación de IP post-redirect
- **run_script sandbox**: bloquea fetch/XHR/WebSocket en scripts inyectados
- **Path traversal protegido**: todos los servers validan rutas contra directorios permitidos
- **SQL injection prevenido**: parámetros parametrizados + CHECK constraints
- **Atomic writes**: credenciales escritas via tempfile + rename
- **Rate limiting**: detección y backoff automático en LinkedIn
- **Protección de Protocolo MCP**: Salida de logs dirigida a `stderr` para evitar corrupciones en el canal JSON-RPC (`stdout`).
- **Concurrencia DB (Thread-Safe)**: Manejo de conexiones SQLite aisladas por hilo (thread-local) con modo WAL habilitado.

## Tests — 113 tests, todos pasando

El proyecto cuenta con una suite de pruebas utilizando `pytest` y `pytest-asyncio`. Las pruebas incluyen fixtures automatizados con bases de datos en memoria para no afectar el entorno local.

```bash
pytest tests/ -v
```

| Suite | Tests | Cobertura |
|---|---|---|
| Database | 6 | Inicialización, admin, FTS, idempotencia |
| Applications | 7 | CRUD, stats, status patch |
| Profiles | 5 | CRUD, delete protection |
| Form Filler | 19 | Inferencia de tipos, parseo, generación de respuestas |
| Static Engine | 14 | Links, extract, forms, labels, navegación |
| Page Scraper | 5 | Scrape, selectores, meta, inspect |
| Table Scraper | 4 | Headers, no headers, selector personalizado |
| List Scraper | 4 | Items, links, campos opcionales |
| Exporters | 7 | CSV, Markdown, sanitización formula injection |
| Tools | 5 | Integración apps + perfiles |
| URL Validation | 11 | SSRF, IPs privadas, localhost, dominios internos |

## Tech Stack

- **Python** `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio JSON-RPC
- **Engines**: Selenium, Playwright, BeautifulSoup, httpx
- **AI Providers**: Google Gemini, Groq, Cerebras
- **PDF**: PyMuPDF, ReportLab, pypdf
- **DB**: SQLite con FTS5

## Project Structure

```
mcp-servers/
├── servers/            # Entry points (browser, route, scrape, doc, linkedin, pathwise)
├── engines/            # Browser engines (compartido con BrowserMCP)
├── router/             # AI Router + providers
│   └── providers/      # Google, Groq, Cerebras
├── scrapers/           # Web scrapers (base, page, table, list, sitemap)
├── docmcp/             # PDF processing (reader, manipulator, generator)
├── database/           # SQLite persistence
│   └── repos/          # applications, profiles
├── tools/              # MCP tool definitions (profile, job, application, cover letter, CV, auto-apply, interview)
├── services/           # Business logic (AI, CV, form filler, job search, company research)
│   └── scrapers/       # Job board scrapers (ChileTrabajos, Computrabajo, etc.)
├── tests/              # 113 tests
├── github_server.py    # GitHub API server
├── filesystem_server.py
└── pyproject.toml
```

## Recent Improvements

### Seguridad
- Credenciales LinkedIn eliminadas del disco — solo env vars
- Passwords con salted SHA256 (no más hash sin sal)
- `.gitignore` excluye `data/` para prevenir filtraciones

### Confiabilidad
- `click_by_text` y `run_script` reparados en Playwright (estaban rotos)
- Método duplicado `click_by_text` eliminado de Selenium
- Fallback `_should_apply` ahora omite postulación si falla AI check
- Caché in-memory con TTL en scrapers (300s default)
- Rate limiting integrado en scraper base

### Escalabilidad
- GitHub API con paginación real (hasta 200 resultados)
- Filesystem server con lectura por chunks (offset/limit)
- Deduplicación de ofertas por título + compañía + locación
- Salario configurable via `DEFAULT_SALARY` env var

### Testing
- 54 tests nuevos (113 totales)
- Cobertura: static engine, scrapers, exporters, tools, integración

### Arquitectura
- BrowserMCP unificado: ahora es un shim que importa de `mcp-servers`
- Sin duplicación de engines entre repos

## License

MIT
