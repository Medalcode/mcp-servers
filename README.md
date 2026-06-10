# MCP Servers — Unified MCP Monorepo

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-134%20passing-success.svg)]()

> **Última actualización**: 9 Junio 2026 — Refactor completo de AI Provider, nuevos scrapers, robustez general.
[![Lint](https://img.shields.io/badge/lint-ruff-passing-brightgreen.svg)]()

Monorepo unificado con 11 servidores MCP (Model Context Protocol) + herramientas de carrera Pathwise.

## Servers

| Server | CLI | Description |
|---|---|---|
| **BrowserMCP** | `browsermcp` | Automatización de navegador con triple motor (Selenium, Playwright, estático) |
| **RouteMCP** | `routemcp` | Router de IA multi-provider (Gemini, Groq, Cerebras) con failover |
| **ScrapeMCP** | `scrapemcp` | Web scraping estructurado con protección SSRF + caché |
| **DocMCP** | `docmcp` | Manipulación de PDFs: leer, mergear, dividir, comprimir, generar |
| **LinkedInMCP** | `linkedinmcp` | Búsqueda y aplicación en LinkedIn (solo env vars, sin credenciales en disco) |
| **Pathwise** | `pathwise` | Plataforma de carrera: perfiles, CV, cover letters, auto-apply |
| **MemoryMCP** | `memorymcp` | Memoria persistente: guarda contexto, decisiones y patrones entre sesiones |
| **GitHubMCP** | `githubmcp` | GitHub: issues, PRs, branches, workflows, commits desde el chat |
| **DatabaseMCP** | `databasemcp` | Consultas SQLite y DuckDB con resultados formateados en tabla |
| **EmailMCP** | `emailmcp` | Gmail: buscar, leer, enviar, borradores, labels, threads |
| **TaskTracker** | `tasktracker` | TODO persistente con prioridades, deadlines, dependencias y brainstorm |
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
memorymcp       # Persistent memory
githubmcp       # GitHub management
databasemcp     # SQLite/DuckDB queries
emailmcp        # Gmail client
tasktracker     # Task management

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

## Tests — 134 tests, todos pasando

El proyecto cuenta con una suite de pruebas utilizando `pytest` y `pytest-asyncio`. Las pruebas incluyen fixtures automatizados con bases de datos en memoria para no afectar el entorno local.

```bash
pytest tests/ -v
```

| Suite | Tests | Cobertura |
|---|---|---|
| Database | 6 | Inicialización, admin, FTS, CHECK constraint |
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
| Memory | 8 | CRUD, búsqueda, categorías, stats |
| Tasks | 8 | CRUD, dependencias, stats |
| Database MCP | 3 | SQLite queries, tablas, describe |

## Tech Stack

- **Python** `>=3.11`
- **Framework**: `mcp` (FastMCP) via stdio JSON-RPC
- **Engines**: Selenium, Playwright, BeautifulSoup, httpx
- **AI Providers**: Google Gemini, Groq, Cerebras
- **PDF**: PyMuPDF, ReportLab, pypdf
- **DB**: SQLite con FTS5, DuckDB (opcional)

## Project Structure

```
mcp-servers/
├── servers/            # Entry points (browser, route, scrape, doc, linkedin, pathwise, memory, github, database, email, task)
├── engines/            # Browser engines (compartido con BrowserMCP)
├── router/             # AI Router + providers
│   └── providers/      # Google, Groq, Cerebras
├── scrapers/           # Web scrapers (base, page, table, list, sitemap)
├── docmcp/             # PDF processing (reader, manipulator, generator)
├── database/           # SQLite persistence
│   └── repos/          # applications, profiles
├── memory_engine/      # Memory/Knowledge graph (SQLite + search)
├── gh_mcp/             # GitHub API client
├── db_mcp/             # SQLite + DuckDB query engine
├── email_mcp/          # Gmail API client
├── task_tracker/       # Persistent task manager with deps
├── tools/              # MCP tool definitions (profile, job, application, cover letter, CV, auto-apply, interview)
├── services/           # Business logic (AI, CV, form filler, job search, company research, browser client)
│   └── scrapers/       # Job board scrapers (BeBee, Randstad, GetOnBoard, Indeed, etc.)
├── tests/              # 134 tests
├── github_server.py    # GitHub API server
├── filesystem_server.py
└── pyproject.toml
```

## Recent Improvements

### 2026-06-09 — Refactor AI Provider + nuevos scrapers + robustez
- **AI Provider reescrito**: `RouterEngine` + fallback Groq → Gemini → Cerebras. Sin dependencia de RouteMCP HTTP.
- **Browser Client unificado**: `services/browser_client.py` elimina 200+ líneas de código duplicado entre LinkedIn y Auto-Apply.
- **Nuevos scrapers**: BeBee (vía API pública), Randstad (extracción JSON SSR).
- **GetOnBoard reparado**: URLs de API corregidas + selectores HTML actualizados.
- **Form Filler mejorado**: `generate_radio_answer` corrige "Si" → "Sí"; `generate_select_answer` salta placeholders, prioriza contexto (escolaridad, género, año).
- **`.env` con ruta absoluta**: los 11 servidores cargan `.env` desde el directorio del proyecto, no del CWD.
- **CHECK constraint** en `status` de applications: validación a nivel DB.
- **Easy Apply loop**: verificación de modal cerrado tras cada click para evitar ciclos infinitos.
- **Job tools**: warning cuando se truncan resultados >25.
- **134/134 tests pasando** (el test de IntegrityError ahora funciona gracias al CHECK constraint).

### 2026-06 — 5 nuevos servidores MCP + limpieza masiva
- **MemoryMCP**: memoria persistente con SQLite (key-value, búsqueda, contextos por sesión)
- **GitHubMCP**: issues, PRs, branches, workflows, commits desde el chat
- **DatabaseMCP**: consultas SQLite y DuckDB con resultados formateados
- **EmailMCP**: Gmail (buscar, leer, enviar, borradores, labels, threads)
- **TaskTracker**: TODO persistente con prioridades, deadlines, dependencias y brainstorm

### Seguridad
- **5 secrets hardcodeados eliminados** de opencode.jsonc → ahora vía env vars + `.env`
- `load_dotenv()` agregado a los 11 servidores
- `.env.example` con todas las variables documentadas
- Credenciales LinkedIn eliminadas del disco — solo env vars
- Passwords con salted SHA256 (no más hash sin sal)
- `.gitignore` excluye `data/` para prevenir filtraciones

### Calidad de código
- **64 lint errors → 0** (ruff): imports inusados, vars sin usar, f-strings, redefiniciones
- Métodos duplicados `click_by_text`/`run_script` eliminados de engines
- `github_server.py` arreglado para compatibilidad Python 3.11
- `_clean_json` undefined corregido en auto_apply_tools
- CI actualizado: `py_compile` → `ruff check` + `pytest`

### Confiabilidad
- `click_by_text` y `run_script` reparados en Playwright (estaban rotos)
- Fallback `_should_apply` ahora omite postulación si falla AI check
- Caché in-memory con TTL en scrapers (300s default)
- Rate limiting integrado en scraper base

### Escalabilidad
- GitHub API con paginación real (hasta 200 resultados)
- Filesystem server con lectura por chunks (offset/limit)
- Deduplicación de ofertas por título + compañía + locación
- Salario configurable via `DEFAULT_SALARY` env var

### Testing
- 134 tests totales (+21 nuevos): memory, tasks, db_mcp
- Cobertura: static engine, scrapers, exporters, tools, integración

### Arquitectura
- BrowserMCP unificado: ahora es un shim que importa de `mcp-servers`
- Sin duplicación de engines entre repos

## License

MIT
