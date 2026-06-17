# NOTE: Playwright is unavailable on Ubuntu 26.04. Use Selenium engine instead (BROWSER_ENGINE=selenium).

import asyncio
import logging
import re
from urllib.parse import urlparse

from engines.base import BrowserEngine, PageResult, LinkInfo, FormInfo, FormField

logger = logging.getLogger(__name__)


class PlaywrightEngine(BrowserEngine):
    name = "playwright"

    def __init__(self):
        self._page = None
        self._browser = None
        self._playwright = None
        self._available = False
        self._loop = None

    async def _ensure_browser(self):
        if self._page:
            return True
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            self._available = True
            return True
        except Exception:
            self._available = False
            return False

    def _sync_run(self, coro):
        try:
            loop = asyncio.get_running_loop()
            has_running_loop = loop.is_running()
        except RuntimeError:
            has_running_loop = False
        if has_running_loop:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
            return self._loop.run_until_complete(coro)
        return asyncio.run(coro)

    def navigate(self, url: str) -> PageResult:
        if not self._sync_run(self._ensure_browser()):
            return PageResult(url=url, title="", html="", text="", error="Playwright not available on this system")
        try:
            self._sync_run(self._page.goto(url, wait_until="networkidle"))
            title = self._sync_run(self._page.title())
            html = self._sync_run(self._page.content())
            text = self._sync_run(self._page.evaluate("() => document.body.innerText"))
            text = re.sub(r"\s+", " ", text)
            text_max = int(__import__('os').environ.get("BROWSER_TEXT_MAX", "15000"))
            text = text[:text_max]
            return PageResult(
                url=self._page.url,
                title=title,
                html=html,
                text=text,
            )
        except Exception as e:
            return PageResult(url=url, title="", html="", text="", error=str(e))

    def extract(self, selector: str) -> list[str]:
        if not self._page:
            return []
        try:
            elements = self._sync_run(self._page.query_selector_all(selector))
            return [self._sync_run(el.inner_text()) for el in elements]
        except Exception:
            return []

    def get_links(self) -> list[LinkInfo]:
        if not self._page:
            return []
        try:
            links = self._sync_run(self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                    href: a.href,
                    text: a.innerText.trim(),
                }));
            }"""))
            base_netloc = urlparse(self._page.url).netloc
            return [
                LinkInfo(href=ln["href"], text=ln["text"], is_internal=urlparse(ln["href"]).netloc == base_netloc)
                for ln in links
            ]
        except Exception:
            return []

    def get_forms(self) -> list[FormInfo]:
        if not self._page:
            return []
        try:
            forms_data = self._sync_run(self._page.evaluate("""() => {
                return Array.from(document.querySelectorAll('form')).map(f => ({
                    action: f.action,
                    method: f.method,
                    fields: Array.from(f.querySelectorAll('input, textarea, select')).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        name: el.name,
                        type: el.type || el.tagName.toLowerCase(),
                        label: (() => {
                            const label = document.querySelector(`label[for="${el.id}"]`);
                            if (label) return label.innerText.trim();
                            const parent = el.closest('label');
                            if (parent) return parent.innerText.trim();
                            return '';
                        })(),
                        required: el.required,
                    })),
                }));
            }"""))
            return [
                FormInfo(
                    action=f["action"],
                    method=f["method"].upper(),
                    fields=[FormField(**fd) for fd in f["fields"]],
                )
                for f in forms_data
            ]
        except Exception:
            return []

    def screenshot(self) -> bytes | None:
        if not self._page:
            return None
        try:
            return self._sync_run(self._page.screenshot(full_page=True))
        except Exception:
            return None

    def click(self, selector: str) -> str:
        if not self._page:
            return "Browser not available"
        try:
            el = self._sync_run(self._page.query_selector(selector))
            if el:
                self._sync_run(el.scroll_into_view_if_needed())
            self._sync_run(self._page.click(selector))
            return f"Clicked: {selector}"
        except Exception as e:
            return f"Click failed: {e}"

    def click_by_text(self, text: str) -> str:
        if not self._page:
            return "Browser not available"
        try:
            patterns = text.split("|")
            for pattern in patterns:
                locator = self._page.get_by_text(pattern.strip(), exact=False)
                if self._sync_run(locator.count()) > 0:
                    self._sync_run(locator.first.click())
                    return f"Clicked text: {pattern.strip()}"
            return f"No element found matching text: {text}"
        except Exception as e:
            return f"click_by_text failed: {e}"

    def run_script(self, script: str) -> str:
        if not self._page:
            return "Browser not available"
        try:
            result = self._sync_run(self._page.evaluate(script))
            return str(result) if result is not None else ""
        except Exception as e:
            return f"run_script failed: {e}"

    def fill(self, selector: str, value: str) -> str:
        if not self._page:
            return "Browser not available"
        try:
            el = self._sync_run(self._page.query_selector(selector))
            if el:
                self._sync_run(el.scroll_into_view_if_needed())
            self._sync_run(self._page.fill(selector, value))
            return f"Filled {selector} = {value}"
        except Exception as e:
            return f"Fill failed: {e}"

    def scroll(self, direction: str) -> str:
        if not self._page:
            return "Browser not available"
        direction = direction.lower()
        try:
            if direction == "bottom":
                self._sync_run(self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)"))
            elif direction == "top":
                self._sync_run(self._page.evaluate("window.scrollTo(0, 0)"))
            else:
                amount = {"down": 500, "up": -500}.get(direction, 500)
                self._sync_run(self._page.evaluate(f"window.scrollBy(0, {amount})"))
            return f"Scrolled {direction}"
        except Exception as e:
            return f"Scroll failed: {e}"

    def wait(self, ms: int) -> str:
        if not self._page:
            return "Browser not available"
        try:
            self._sync_run(self._page.wait_for_timeout(ms))
            return f"Waited {ms}ms"
        except Exception as e:
            return f"Wait failed: {e}"

    def close(self):
        try:
            if self._browser:
                self._sync_run(self._browser.close())
        except Exception as e:
            logger.debug("playwright browser close failed: %s", e)
        try:
            if self._playwright:
                self._sync_run(self._playwright.stop())
        except Exception as e:
            logger.debug("playwright stop failed: %s", e)
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.close()
            except Exception as e:
                logger.debug("loop close failed: %s", e)
        self._page = None
        self._browser = None
        self._playwright = None
        self._available = False
        self._loop = None
