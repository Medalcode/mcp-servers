# Graph Report - D:\Github\mcp-servers  (2026-07-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1000 nodes · 2323 edges · 56 communities (48 shown, 8 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 109 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f47ee85a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- auto_apply_tools.py
- __init__.py
- scrape.py
- api_server.py
- call_tool
- browser.py
- github_mcp.py
- RouterEngine
- run_server
- doc.py
- StaticEngine
- memory.py
- init_db
- gmail.py
- database_mcp.py
- SeleniumEngine
- PlaywrightEngine
- _css_escape
- EmailVerificationReader
- BrowserEngine
- app.js
- _validate_url
- get_connection
- selenium_engine.py
- profiles.py
- config.py
- _check_path
- attempt_auto_login
- conftest.py
- auto_apply_standalone.py
- interview_tools.py
- test_database.py
- local_agent.py
- application_tools.py
- start.sh
- start_dashboard.sh
- medalcode-mcp-servers

## God Nodes (most connected - your core abstractions)
1. `SeleniumEngine` - 52 edges
2. `StaticEngine` - 38 edges
3. `call_tool()` - 37 edges
4. `init_db()` - 33 edges
5. `FormQuestion` - 33 edges
6. `get_connection()` - 27 edges
7. `scan_duckduckgo()` - 25 edges
8. `RouterEngine` - 24 edges
9. `run_server()` - 24 edges
10. `PlaywrightEngine` - 23 edges

## Surprising Connections (you probably didn't know these)
- `ConnectionManager` --uses--> `SeleniumEngine`  [INFERRED]
  api_server.py → engines/selenium_engine.py
- `ConnectionManager` --uses--> `RouterEngine`  [INFERRED]
  api_server.py → router/engine.py
- `SearchRequest` --uses--> `SeleniumEngine`  [INFERRED]
  api_server.py → engines/selenium_engine.py
- `SearchRequest` --uses--> `RouterEngine`  [INFERRED]
  api_server.py → router/engine.py
- `RegisterRequest` --uses--> `SeleniumEngine`  [INFERRED]
  api_server.py → engines/selenium_engine.py

## Import Cycles
- None detected.

## Communities (56 total, 8 thin omitted)

### Community 0 - "auto_apply_tools.py"
Cohesion: 0.06
Nodes (40): answer_form_question(), _call_ai(), _clean_json(), generate_cover_letter(), generate_personas(), _get_engine(), parse_cv_with_ai(), tailor_cv_pdf() (+32 more)

### Community 1 - "__init__.py"
Cohesion: 0.06
Nodes (49): BeautifulSoup, main(), _call_scrapemcp(), _get_scrapemcp_url(), get_stats(), _is_scrapemcp_enabled(), _matches_location(), _run_scraper_with_retry() (+41 more)

### Community 2 - "scrape.py"
Cohesion: 0.05
Nodes (35): BaseScraper, ScrapeResult, _sanitize(), to_csv(), to_markdown(), ListScraper, PageScraper, SitemapScraper (+27 more)

### Community 3 - "api_server.py"
Cohesion: 0.07
Nodes (49): add_log(), api_apply(), api_batch_apply(), api_register(), api_search(), api_set_model(), ApplyRequest, BatchApplyRequest (+41 more)

### Community 4 - "call_tool"
Cohesion: 0.07
Nodes (48): main(), Debug login flow on Trabajando.com., safe(), main(), Job search + apply using browser client directly., safe(), try_apply(), main() (+40 more)

### Community 5 - "browser.py"
Cohesion: 0.07
Nodes (26): click(), click_by_text(), _dns_cache_cleanup(), _dns_cache_set(), _dns_resolves(), engine_info(), _engine_prefix(), _ensure_engine() (+18 more)

### Community 6 - "github_mcp.py"
Cohesion: 0.09
Nodes (37): _check_token(), close_issue(), create_issue(), _get(), _get_client(), get_file_content(), _get_headers(), get_issue() (+29 more)

### Community 7 - "RouterEngine"
Cohesion: 0.08
Nodes (18): api_models(), Exception, classify(), RouterEngine, load_config(), ModelInfo, AIProvider, ProviderError (+10 more)

### Community 8 - "run_server"
Cohesion: 0.11
Nodes (38): main(), main(), main(), main(), main(), FastMCP, run_server(), main() (+30 more)

### Community 9 - "doc.py"
Cohesion: 0.10
Nodes (19): PDFGenerator, PDFManipulator, PDFReader, _safe_open(), Document, compress(), extract_images(), extract_pages() (+11 more)

### Community 10 - "StaticEngine"
Cohesion: 0.11
Nodes (17): StaticEngine, MockResponse, MockSession, test_static_engine_click_returns_message(), test_static_engine_extract(), test_static_engine_extract_empty(), test_static_engine_fill_returns_message(), test_static_engine_forms() (+9 more)

### Community 11 - "memory.py"
Cohesion: 0.17
Nodes (28): forget(), get_categories(), _get_conn(), get_context(), list_by_category(), Any, recall(), remember() (+20 more)

### Community 12 - "init_db"
Cohesion: 0.15
Nodes (22): init_db(), test_create_application(), test_delete_application(), test_get_application(), test_get_stats(), test_list_applications(), test_patch_status(), test_update_application() (+14 more)

### Community 13 - "gmail.py"
Cohesion: 0.20
Nodes (22): _check_token(), _decode_body(), draft(), _format_email(), _get(), _get_refresh_config(), _get_token(), list_labels() (+14 more)

### Community 14 - "database_mcp.py"
Cohesion: 0.19
Nodes (19): describe_sqlite_table(), _format_results(), _get_duckdb_conn(), _get_sqlite_conn(), list_duckdb_tables(), list_sqlite_tables(), Any, Connection (+11 more)

### Community 15 - "SeleniumEngine"
Cohesion: 0.17
Nodes (3): _detect_chromedriver(), _detect_chromium_binary(), SeleniumEngine

### Community 17 - "_css_escape"
Cohesion: 0.23
Nodes (4): TestCssEscape, TestSafeSelector, _css_escape(), _safe_selector()

### Community 18 - "EmailVerificationReader"
Cohesion: 0.20
Nodes (5): EmailVerificationReader, Attempts to extract a verification code from email body., Fetches the latest verification code., Attempts to register a new account on a SuccessFactors portal., SuccessFactorsAutomator

### Community 20 - "app.js"
Cohesion: 0.27
Nodes (10): loadModels(), logToConsole(), pollTask(), renderTable(), showErrorInTable(), startApply(), startBatchApply(), startDirectApply() (+2 more)

### Community 22 - "get_connection"
Cohesion: 0.33
Nodes (10): get_connection(), Connection, create_application(), delete_application(), get_application(), get_stats(), list_applications(), patch_status() (+2 more)

### Community 23 - "selenium_engine.py"
Cohesion: 0.38
Nodes (5): FormField, FormInfo, LinkInfo, PageResult, # NOTE: Playwright is unavailable on Ubuntu 26.04. Use Selenium engine instead (

### Community 24 - "profiles.py"
Cohesion: 0.29
Nodes (9): create_profile(), delete_profile(), get_default_profile(), get_full_profile(), list_profiles(), _row_to_camel(), save_parsed_cv(), _to_camel() (+1 more)

### Community 25 - "config.py"
Cohesion: 0.28
Nodes (4): get_data_dir(), get_db_path(), Path, _seed_default_profile()

### Community 26 - "_check_path"
Cohesion: 0.39
Nodes (8): _check_path(), delete_file(), file_info(), list_directory(), Path, read_file(), search_files(), write_file()

### Community 27 - "attempt_auto_login"
Cohesion: 0.39
Nodes (5): main(), main(), main(), attempt_auto_login(), Attempts to log in to the portal matching the URL.     Returns True if login wa

### Community 28 - "conftest.py"
Cohesion: 0.29
Nodes (5): db_connection(), pytest_configure(), Provide a fresh temporary database for each test., Configure test environment before any collection., _test_db()

### Community 29 - "auto_apply_standalone.py"
Cohesion: 0.53
Nodes (4): click(), firstjob(), getonboard(), successfactors()

### Community 30 - "interview_tools.py"
Cohesion: 0.67
Nodes (4): get_company_insights(), research_company(), FastMCP, register_tools()

### Community 32 - "local_agent.py"
Cohesion: 0.83
Nodes (3): parse_tool_call(), run(), run_tool()

## Knowledge Gaps
- **3 isolated node(s):** `medalcode-mcp-servers`, `start.sh script`, `start_dashboard.sh script`
  These have ≤1 connection - possible missing edges or undocumented components.
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `run_server()` connect `run_server` to `scrape.py`, `call_tool`, `browser.py`, `github_mcp.py`, `RouterEngine`, `doc.py`, `memory.py`, `gmail.py`, `database_mcp.py`?**
  _High betweenness centrality (0.236) - this node is a cross-community bridge._
- **Why does `SeleniumEngine` connect `SeleniumEngine` to `auto_apply_tools.py`, `api_server.py`, `call_tool`, `browser.py`, `EmailVerificationReader`, `BrowserEngine`, `selenium_engine.py`, `attempt_auto_login`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Why does `StaticEngine` connect `StaticEngine` to `BrowserEngine`, `browser.py`, `selenium_engine.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `SeleniumEngine` (e.g. with `ApplyRequest` and `BatchApplyRequest`) actually correct?**
  _`SeleniumEngine` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `StaticEngine` (e.g. with `BrowserEngine` and `FormField`) actually correct?**
  _`StaticEngine` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `FormQuestion` (e.g. with `SeleniumEngine` and `TestGenerateAnswer`) actually correct?**
  _`FormQuestion` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `# NOTE: Playwright is unavailable on Ubuntu 26.04. Use Selenium engine instead (`, `medalcode-mcp-servers`, `Debug login flow on Trabajando.com.` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._