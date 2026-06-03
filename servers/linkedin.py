import asyncio
import json
import logging
import os
import sys
import time
import signal
from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("LinkedIn MCP")

_browser_proc = None
_browser_proc_lock = asyncio.Lock()
_next_req_id = 1
_req_id_lock = asyncio.Lock()
_linkedin_ready = False

MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


async def _next_id() -> int:
    global _next_req_id
    async with _req_id_lock:
        cur = _next_req_id
        _next_req_id += 1
        return cur


async def _consume_stderr(proc):
    try:
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            text = line.decode().rstrip()
            if text:
                logger.debug("BrowserMCP stderr: %s", text)
    except Exception:
        pass


async def _read_json_response(proc, timeout=60):
    buf = ""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=min(5.0, remaining))
        except asyncio.TimeoutError:
            continue
        if not line:
            break
        buf += line.decode()
        try:
            return json.loads(buf)
        except json.JSONDecodeError:
            continue
    raise TimeoutError("No valid JSON response from browser")


async def _browser_call(method: str, params: dict = None, timeout: float = 120):
    global _browser_proc
    req_id = await _next_id()
    req = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {"name": method, "arguments": params or {}},
            }
        )
        + "\n"
    )
    _browser_proc.stdin.write(req.encode())
    await _browser_proc.stdin.drain()
    while True:
        resp = await _read_json_response(_browser_proc, timeout=timeout)
        if resp.get("id") == req_id:
            if "error" in resp:
                raise RuntimeError(f"BrowserMCP error: {resp['error']}")
            content = resp.get("result", {}).get("content", [])
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts)
        logger.debug("Skipping response for id=%s (waiting for %s)", resp.get("id"), req_id)


async def _browser_start():
    global _browser_proc
    async with _browser_proc_lock:
        if _browser_proc is not None and _browser_proc.returncode is None:
            return
        env = {**os.environ, "BROWSER_ENGINE": "selenium", "CHROME_DEBUG_PORT": "9226"}
        _browser_proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m", "servers.browser",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=MCP_DIR,
            env=env,
        )
        asyncio.ensure_future(_consume_stderr(_browser_proc))
        init_req = (
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "linkedinmcp", "version": "0.1.0"},
                    },
                }
            )
            + "\n"
        )
        _browser_proc.stdin.write(init_req.encode())
        await _browser_proc.stdin.drain()
        resp = await _read_json_response(_browser_proc, timeout=10)
        logger.info(
            "BrowserMCP initialized: %s",
            str(resp.get("result", {}))[:80] if resp else "None",
        )
        initialized = (
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
            + "\n"
        )
        _browser_proc.stdin.write(initialized.encode())
        await _browser_proc.stdin.drain()


async def _browser_stop():
    global _browser_proc
    if _browser_proc is not None and _browser_proc.returncode is None:
        try:
            _browser_proc.send_signal(signal.SIGTERM)
            await asyncio.wait_for(_browser_proc.wait(), timeout=10)
        except Exception:
            try:
                _browser_proc.kill()
            except Exception:
                pass
        _browser_proc = None


async def _ensure_linkedin_session(email: str = None, password: str = None):
    global _linkedin_ready
    if _linkedin_ready:
        return

    await _browser_start()
    await _browser_call("navigate", {"url": "https://www.linkedin.com"})
    await _browser_call("wait", {"ms": 2000})
    page_text = await _browser_call("extract", {"selector": "body"})

    if "sign in" not in page_text.lower() and "feed" in page_text.lower():
        _linkedin_ready = True
        logger.info("Already logged in to LinkedIn")
        return

    email = email or os.environ.get("LINKEDIN_EMAIL")
    password = password or os.environ.get("LINKEDIN_PASSWORD")

    if not email or not password:
        raise RuntimeError(
            "LinkedIn credentials required. Provide email/password to linkedin_login() "
            "or set LINKEDIN_EMAIL/LINKEDIN_PASSWORD env vars."
        )

    logger.info("Logging in to LinkedIn...")
    await _browser_call("navigate", {"url": "https://www.linkedin.com/login"})
    await _browser_call("wait", {"ms": 2000})
    await _browser_call("fill", {"selector": "#username", "value": email})
    await _browser_call("fill", {"selector": "#password", "value": password})
    await _browser_call("click", {"selector": "button[type=submit]"})
    await _browser_call("wait", {"ms": 5000})

    check = await _browser_call("extract", {"selector": "body"})
    if "checkpoint" in check.lower() or "security" in check.lower():
        raise RuntimeError("LinkedIn requires security verification - log in manually via Chrome")

    _linkedin_ready = True
    logger.info("LinkedIn login successful")


@mcp.tool()
async def linkedin_login(email: str = None, password: str = None) -> str:
    """Log in to LinkedIn. Credentials saved for future use. Falls back to LINKEDIN_EMAIL/LINKEDIN_PASSWORD env vars."""
    global _linkedin_ready
    _linkedin_ready = False
    try:
        await _ensure_linkedin_session(email, password)
        return "Logged in to LinkedIn successfully"
    except Exception as e:
        return f"Login failed: {e}"


@mcp.tool()
async def linkedin_search_jobs(
    keywords: str, location: str = "Chile", remote_only: bool = True, limit: int = 10
) -> str:
    """Search for jobs on LinkedIn. Returns title, company, location, and apply link for each result."""
    await _ensure_linkedin_session()
    params = f"keywords={keywords.replace(' ', '%20')}&location={location.replace(' ', '%20')}"
    if remote_only:
        params += "&f_WT=2"
    url = f"https://www.linkedin.com/jobs/search/?{params}"
    await _browser_call("navigate", {"url": url})
    await _browser_call("wait", {"ms": 3000})

    result = await _browser_call(
        "run_script",
        {"script": f"""
            const items = document.querySelectorAll('.job-card-container, .jobs-search-results__list li');
            const jobs = [];
            for(const item of items) {{
                const title = item.querySelector('.job-card-list__title, .job-card-container__link');
                const company = item.querySelector('.job-card-container__company-name');
                const loc = item.querySelector('.job-card-container__metadata-item');
                const link = title?.closest('a') || title?.querySelector('a');
                if(title) {{
                    const href = link ? (link.href || link.getAttribute('href')) : '';
                    jobs.push({{
                        title: (title.textContent || '').trim(),
                        company: (company?.textContent || '').trim(),
                        location: (loc?.textContent || '').trim(),
                        url: href
                    }});
                }}
            }}
            return JSON.stringify(jobs.slice(0, {limit}));
        """},
    )

    try:
        jobs = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return f"Could not parse results:\n{result[:2000]}"

    if not jobs:
        return "No jobs found. Try different keywords or location."

    lines = [f"Found {len(jobs)} jobs:\n"]
    for i, job in enumerate(jobs, 1):
        lines.append(f"{i}. {job.get('title', 'N/A')}")
        lines.append(f"   {job.get('company', 'N/A')} - {job.get('location', 'N/A')}")
        if job.get("url"):
            lines.append(f"   {job['url']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def linkedin_get_job_details(url: str) -> str:
    """Get full job description, company, location, and criteria from a LinkedIn job posting."""
    await _ensure_linkedin_session()
    await _browser_call("navigate", {"url": url})
    await _browser_call("wait", {"ms": 3000})

    result = await _browser_call(
        "run_script",
        {"script": """
            const title = document.querySelector('.job-details-jobs-unified-top-card__job-title, h1');
            const company = document.querySelector('.job-details-jobs-unified-top-card__company-name a, .job-details-top-card__company-name');
            const location = document.querySelector('.job-details-jobs-unified-top-card__bullet, .job-details-top-card__location');
            const desc = document.querySelector('.jobs-description__content, .show-more-less-html__markup, .job-details-jobs-unified-top-card__description');
            const criteria = document.querySelectorAll('.job-details-jobs-unified-top-card__job-inset span');
            return JSON.stringify({
                title: title?.textContent?.trim() || 'N/A',
                company: company?.textContent?.trim() || 'N/A',
                location: location?.textContent?.trim() || 'N/A',
                criteria: Array.from(criteria).map(c=>c.textContent.trim()).filter(Boolean).join(' | ') || 'N/A',
                description: desc?.innerText?.trim()?.substring(0, 3000) || 'No description'
            });
        """},
    )

    try:
        d = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        return f"Could not parse details:\n{result[:2000]}"

    return (
        f"Title: {d.get('title')}\n"
        f"Company: {d.get('company')}\n"
        f"Location: {d.get('location')}\n"
        f"Criteria: {d.get('criteria')}\n"
        f"---\n{d.get('description')}"
    )


@mcp.tool()
async def linkedin_scroll() -> str:
    """Scroll down on LinkedIn jobs page to load more results."""
    await _ensure_linkedin_session()
    return await _browser_call("scroll", {"direction": "down"})


@mcp.tool()
async def linkedin_check_easy_apply(url: str) -> str:
    """Check if a LinkedIn job posting has an Easy Apply button."""
    await _ensure_linkedin_session()
    await _browser_call("navigate", {"url": url})
    await _browser_call("wait", {"ms": 3000})

    result = await _browser_call(
        "run_script",
        {"script": """
            const btn = Array.from(document.querySelectorAll('button')).find(b =>
                b.textContent.toLowerCase().includes('easy apply') ||
                b.textContent.toLowerCase().includes('solicitar') ||
                b.textContent.toLowerCase().includes('postular')
            );
            return JSON.stringify({
                hasEasyApply: !!btn,
                buttonText: btn?.textContent?.trim() || ''
            });
        """},
    )
    return result


@mcp.tool()
async def linkedin_easy_apply(url: str, resume_path: str = "") -> str:
    """Apply to a LinkedIn job using Easy Apply. Walks through multi-step form and submits."""
    await _ensure_linkedin_session()
    await _browser_call("navigate", {"url": url})
    await _browser_call("wait", {"ms": 3000})

    has_btn = await _browser_call(
        "run_script",
        {"script": """
            const btn = Array.from(document.querySelectorAll('button')).find(b =>
                b.textContent.toLowerCase().includes('easy apply') ||
                b.textContent.toLowerCase().includes('solicitar') ||
                b.textContent.toLowerCase().includes('postular') ||
                b.textContent.toLowerCase().includes('apply')
            );
            return btn ? 'found' : 'NO_EASY_APPLY';
        """},
    )
    if "NO_EASY_APPLY" in has_btn:
        return "No Easy Apply button found for this job"

    await _browser_call("click_by_text", {"text": "Easy Apply|Solicitar|Postular|Apply"})
    await _browser_call("wait", {"ms": 2000})

    steps = 0
    results = []
    while steps < 10:
        info_raw = await _browser_call(
            "run_script",
            {"script": """
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b =>
                    /next|siguiente|review|submit|enviar|done/i.test(b.textContent)
                );
                const disabled = btn ? btn.disabled || btn.getAttribute('aria-disabled') === 'true' : true;
                return JSON.stringify({hasButton: !!btn, text: btn?.textContent?.trim() || '', disabled});
            """},
        )
        try:
            info = json.loads(info_raw)
        except (json.JSONDecodeError, TypeError):
            info = {"hasButton": False, "disabled": True}

        if not info.get("hasButton"):
            modal = await _browser_call(
                "run_script",
                {"script": "return document.querySelector('.artdeco-modal, .jobs-easy-apply-modal') ? 'open' : 'closed';"},
            )
            if "closed" in modal:
                results.append("Application submitted successfully!")
                break
            fields = await _browser_call("forms", {})
            results.append(f"Step {steps+1} fields:\n{fields}")
            await _browser_call("click_by_text", {"text": "Next|Siguiente|Review|Done"})
            await _browser_call("wait", {"ms": 1500})
            steps += 1
            continue

        if info.get("disabled"):
            fields_raw = await _browser_call(
                "run_script",
                {"script": """
                    const inputs = document.querySelectorAll('.jobs-easy-apply-modal input, .jobs-easy-apply-modal select, .jobs-easy-apply-modal textarea');
                    return JSON.stringify(Array.from(inputs).map(i => ({
                        type: i.type || i.tagName, name: i.name || i.id,
                        placeholder: i.placeholder || '',
                        required: i.required || !!i.closest('.fb-form-element')?.querySelector('.fb-required')
                    })));
                """},
            )
            results.append(f"Step {steps+1} requires fields:\n{fields_raw}")

        await _browser_call(
            "click",
            {
                "selector": "button[aria-label*='Next'], button[aria-label*='Siguiente'], button[aria-label*='Review'], button[aria-label*='Submit'], .artdeco-button--primary"
            },
        )
        await _browser_call("wait", {"ms": 2000})
        steps += 1

    result_text = "\n".join(results) if results else "Application flow completed"
    return f"Easy Apply completed in {steps} steps.\n{result_text}"


def main():
    logging.basicConfig(
        stream=sys.stderr,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )
    import atexit

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    atexit.register(lambda: loop.run_until_complete(_browser_stop()))
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
