# MCP Servers — Unified MCP Monorepo

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-199%20passing-success.svg)]()

> **Última actualización**: 2 Julio 2026 — Security Hardening Completo, XSS, SSRF, JS Injection & Race Conditions.
[![Lint](https://img.shields.io/badge/lint-ruff-passing-brightgreen.svg)]()

Monorepo unificado con 12 servidores MCP (Model Context Protocol) + Herramientas avanzadas de carrera Pathwise (Dashboard Gráfico y CLI).

## Servers

| Server | CLI | Description |
|---|---|---|
| **BrowserMCP** | `browsermcp` | Automatización de navegador con triple motor (Selenium, Playwright, estático) |
| **RouteMCP** | `routemcp` | Router de IA multi-provider (Gemini, Groq, Cerebras) con failover |
| **ScrapeMCP** | `scrapemcp` | Web scraping estructurado con protección SSRF + caché. 22 portales de empleo. |
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
| **GraphifyMCP** | `graphifymcp` | Generación y consulta de Knowledge Graph del monorepo |

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
| GraphifyMCP | `http://localhost:8013/sse` |

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
2. Edita el archivo `.env` con tus credenciales (incluyendo `GMAIL_APP_PASS` para la verificación IMAP).
3. Inicia el panel web gráfico (Recomendado):

```bash
./start_dashboard.sh
```
El panel estará disponible en `http://localhost:8010`.

4. O ejecuta los servidores de forma independiente:

```bash
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

python github_server.py
python filesystem_server.py
```

## Seguridad

- **JS injection prevention**: credenciales escapadas con `json.dumps()` en lugar de f-strings
- **CSS selector sanitization**: helpers `_css_escape()`/`_safe_selector()` evitan inyección en selectores
- **Env whitelist**: browser subprocess hereda solo 18 vars seguras
- **URL validation**: rechaza credenciales embebidas, IPs privadas, hostnames no resolubles
- **Script sandbox**: blocklist de APIs peligrosas (`eval`, `Function`, `fetch`, `WebSocket`, etc.)
- **DNS rebinding prevention**: re-validación de IP post-redirect
- **Path traversal protegido**: todos los servers validan rutas contra directorios permitidos
- **SQL injection prevenido**: parámetros parametrizados + CHECK constraints
- **Atomic writes**: credenciales escritas via tempfile + rename
- **Rate limiting**: detección y backoff automático en LinkedIn
- **Protección de Protocolo MCP**: Salida de logs dirigida a `stderr` para evitar corrupciones en el canal JSON-RPC (`stdout`).
- **Concurrencia DB (Thread-Safe)**: Manejo de conexiones SQLite aisladas por hilo (thread-local) con modo WAL habilitado.

## Tests — 199 tests, todos pasando

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
| Browser Security | 32 | URL validation, script sandbox, DNS, private IPs |
| Auto-Apply Security | 10 | CSS escape, safe selectors |
| Total | 199 | All passing |

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
├── tests/              # 176 tests
├── github_server.py    # GitHub API server
├── filesystem_server.py
└── pyproject.toml
```

## Recent Improvements

### 2026-06-28 — Graphify MCP Integration
- **Architecture**: Se integró formalmente `graphifyy` como el servidor MCP número 12, exponiendo el puerto `8013`. Esto habilita la generación y consulta nativa del Knowledge Graph del monorepo, optimizando la comprensión de la base de código para agentes de IA sin consumir tokens excesivos de contexto.

### 2026-06-26 — Security Remediation & Observability
- **Security**: Remediación crítica de seguridad. Se destrackearon `profile.json` y `config.json` para proteger datos personales y se eliminaron múltiples scripts duplicados (`run_apply*.py`) que exponían credenciales hardcodeadas.
- **Architecture**: Se creó el script unificado `scripts/run_apply_unified.py` que inyecta parámetros vía `.env`.
- **Observability**: Instrumentación del motor de scraping. `scraper_engine.py` ahora expone estadísticas en logs (mediante `get_stats()`) permitiendo diferenciar entre bloqueos WAF (error HTTP) y selectores CSS rotos.
- **Contract Tests**: Incorporación de testing con snapshots HTML mockeados para detectar rupturas silenciosas de selectores en portales de empleo.
### 2026-07-02 — Security Hardening Completo (26 issues corregidos)
- **🔴 5 Críticos eliminados**: Password hardcodeado (`IBM_PASS` fallback removido), JS injection via f-strings (5 archivos), XSS via `innerHTML` en frontend, script validation bypass en engine, SSRF via URL injection en scraper, OAuth token sin refresh.
- **🟠 7 Altos corregidos**: Hardcoded paths de CV reemplazados por `USER_CV_PATH` env var, race condition en `ConnectionManager.broadcast`, WebSocket sin auth (token query param), input validation en Pydantic models (`Field` constraints), stack trace sanitization, IMAP creds leídas lazy, singleton race en `_ensure_engine`.
- **🟡 5 Medios corregidos**: DNS TOCTOU (cache TTL reducido 300→30s + re-validación post-redirect), HTML sanitization con BeautifulSoup en 6 scrapers RSS, `except:` desnudos cambiados a `except Exception`, dead code removido (`_ANSWER_STRATEGIES`, `_get_context_help`), settings endpoint con API token.
- **🟢 9 Bajos corregidos**: Playwright engine con fast-fail en import, static engine sin binarios en texto, Chromium version configurable (`CHROME_VERSION`), reload mode configurable (`API_RELOAD`), formularios de salario sin fallback hardcodeado, `json.dumps()` en form_filler para target/val.
- **Tests**: 199/199 pasando. Arquitectura: validación JS unificada en `SeleniumEngine.run_script()` que cierra el bypass del security layer.

### 2026-06-20 — AI Rate Limiter Resiliency & Application Pipeline Fixes
- **AI Provider Fallback Optimization**: Se parcheó `router/providers/base.py` para abortar proactivamente el proveedor de IA primario (como Groq) si devuelve una cabecera `Retry-After` irracional (por ejemplo, > 10 segundos). Esto evita que los procesos de postulación masiva se congelen durante decenas de minutos y obliga al `RouterEngine` a cambiar dinámicamente a modelos de *fallback* (como Gemini).
- **Prevención de Crash por PDF (NoneType Decode)**: Se resolvió un error silencioso y destructivo (`AttributeError: 'NoneType' object has no attribute 'decode'`) que ocurría en `services/cv_service.py` cuando el proveedor de IA omitía generar alguna clave en el JSON de adaptación del CV. El motor `reportlab` ahora emplea validaciones *string-cast* seguras (`str(value or '')`) en toda la fase de renderizado vectorial.

### 2026-06-19 — Auditoría de Seguridad, Refactorización Asíncrona y Testing (199 Tests)
- **Zero Vulnerabilidades Críticas**: Se solucionó un RCE (Remote Code Execution) mitigando el uso de `shell=True` en `local_agent.py` y se previnieron inyecciones SQL parametrizando los identificadores de tablas en `db_mcp/engine.py`.
- **Arquitectura Asíncrona y Reactiva**: El `api_server.py` abandonó los bloqueos de variables globales en favor de una base de datos SQLite nativa para métricas. Las llamadas pesadas ahora usan `BackgroundTasks` con *Job Polling*, evitando bloqueos del Event Loop y mejorando el Frontend con actualizaciones asíncronas de resultados.
- **Mantenibilidad y Clean Code**: Refactorización de componentes complejos (`form_filler.py`, `scraper_engine.py`) con mapas de estrategia escalables. El repositorio completó exitosamente una migración a `ruff`, resolviendo +1300 advertencias de estilo. Se cuenta ahora con 199 tests ejecutándose y pasando en verde.

### 2026-06-18 — 11 Nuevos Gigantes Corporativos (ATS Bypass)
- **Expansión Global y LatAm**: Añadidos 11 nuevos scrapers corporativos a la lista de DEDICATED_SCRAPERS, incluyendo: **IBM, Microsoft, Nestlé, Coca-Cola, PepsiCo, SAP, Cencosud, Falabella, Latam Airlines, Entel y Banco BCI**.
- **Motor DDG HTML**: Para sortear los estrictos WAFs de plataformas ATS (Workday, SuccessFactors, Eightfold), se diseñó un motor `base_ddg.py` que inyecta dorks nativos a través de DuckDuckGo HTML, extrayendo las vacantes limpias sin tocar los servidores empresariales directamente ni exponer IPs.

### 2026-06-17 — Web UI Dashboard, Profile Sync Pre-Vuelo & Filtros Avanzados
- **Pathwise Dashboard**: Creación de una Interfaz Gráfica interactiva (`frontend/`, `api_server.py`) con diseño Glassmorphism oscuro. Permite orquestar todo el ecosistema (búsqueda, registro, logs en vivo) sin tocar la terminal.
- **Sincronización Pre-Vuelo (Profile Sync)**: El bot ahora intercepta las postulaciones para navegar obligatoriamente a los ajustes del perfil. Inyecta la experiencia y el resumen del CV maestro y cancela el flujo si detecta fallos, protegiendo la reputación del postulante.
- **Filtros Nativos Avanzados**: Incorporados filtros de Búsqueda (Ubicación, Rol, Modalidad, Fecha) que inyectan parámetros URL nativos cuando es soportado (CompuTrabajo) o limpian los resultados con Post-Filtering algorítmico cuando el portal original ignora los parámetros (Trabajando, FirstJob).
- **Intercepción IMAP**: Integración directa con Gmail (`email_reader.py`) que lee códigos PIN en tiempo real para saltarse los bloqueos de registro de SuccessFactors.

### 2026-06-17 — Cloudflare Bypass, Auto-Login & Rellenado de Formularios
- **Cloudflare Bypass**: Implementado el soporte directo para `undetected-chromedriver` dentro del motor interno `SeleniumEngine`. Se corrigieron problemas de cuelgues (timeouts de 60s) habilitando `XAUTHORITY` y pasando correctamente variables de entorno al abrir Chrome visualmente.
- **Auto-Login Integrado**: Se amplió el mapeo de `services/auto_login.py` para detectar proactivamente páginas que exijan inicio de sesión (Computrabajo, Chiletrabajos, IBM, Sonda).
-   **Plataformas Genéricas**: LinkedIn, Computrabajo, Chiletrabajos, Laborum, Indeed, Bebee, FirstJob, GetOnBoard, Randstad, Trabajando.com
-   **Minería (Chile)**: BHP, Codelco, Freeport, Glencore, Lundin, Teck.
-   **Global Giants / LatAm**:
    -   *Retail / Servicios*: Cencosud (Jumbo, Paris), Falabella (Sodimac, Tottus), Latam Airlines, Entel, Banco BCI.
    -   *Tecnología / Consumo*: IBM, Microsoft, SAP, Nestlé, Coca-Cola, PepsiCo.
- **Inyección de Perfil via IA**: Creada la funcionalidad `answer_form_question` que permite responder dinámicamente cualquier campo oculto (radio, textarea, inputs) basándose en el CV subido a la memoria.

### 2026-06-16 — Security Audit, Resource Leaks & Stability Fixes
- **Resource Leaks**: Fixed SQLite connection leaks in `db_mcp/engine.py` using `contextlib.closing` and `task_tracker/engine.py`.
- **Database Safety**: Enforced read-only mode for SQLite and DuckDB queries to prevent destructive SQL execution, and enabled `PRAGMA foreign_keys=ON` for the task tracker.
- **Atomic Operations**: Wrapped profile creation in `database/repos/profiles.py` inside a transaction block.
- **Path Traversal Guards**: Added `CV_ALLOWED_PATH` validation in `tools/cv_tools.py` and fixed variable shadowing in `filesystem_server.py`.
- **Event Loop Leak**: Fixed dangling asyncio event loops in `engines/playwright_engine.py` by properly closing them on exit.
- **Billion Laughs XML**: Replaced `xml.etree` with `defusedxml` in `scrapers/sitemap.py` to mitigate entity expansion attacks.
- **SSRF Protection**: Disabled `follow_redirects` across all scrapers to prevent Server-Side Request Forgery bypasses via HTTP redirects.
- **AI Provider Resiliency**: Added intelligent HTTP 5xx retry logic in `router/providers/base.py` supporting `Retry-After` headers and fixed prompt truncation in `services/ai_provider.py`.
- **Testing**: Updated `test_db_mcp.py` for read-only database support. 176/176 tests passing successfully.

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

### 2026-06-11 — Seguridad, calidad, testing + 42 nuevos tests
- **JS injection prevention**: credenciales escapadas con `json.dumps()` en LinkedIn y Auto-Apply
- **CSS selector sanitization**: helpers `_css_escape()`/`_safe_selector()` en Auto-Apply
- **Env whitelist**: browser subprocess hereda solo 18 vars seguras
- **URL validation reforzado**: rechaza credenciales embebidas, IPs privadas, hostnames sin resolución DNS
- **Script sandbox mejorado**: blocklist de `eval`, `Function`, `setTimeout`, `WebSocket` y más (corregido bug de case-sensitivity que dejaba pasar scripts peligrosos)
- **Import-time `load_dotenv()` eliminado** de scrapers/base.py y la mayoría de los servidores
- **SQLite connection pooling** thread-local con WAL en memory_engine y task_tracker
- **Cycle detection BFS** en dependencias de TaskTracker
- **`run_server()` unificado**: 11 servidores comparten el mismo boilerplate `main()` via `servers/server_base.py`
- **`generate_answer()` refactorizada**: estrategia extraída a `_build_strategies()` con todos los formatos originales
- **Dead code eliminado**: `_extract_textarea_questions()`, dependencia `bcrypt`
- **42 nuevos tests de seguridad**: 32 para browser (URL validation, script sandbox, DNS) + 10 para Auto-Apply (CSS escape, selectors)
- **176/176 tests pasando**

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
