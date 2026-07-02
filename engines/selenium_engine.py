import logging
import re
import shutil
import time
import os
import tempfile
from urllib.parse import urljoin, urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from engines.base import BrowserEngine, PageResult, LinkInfo, FormInfo, FormField

logger = logging.getLogger(__name__)

_uc = None
if os.environ.get("BROWSER_STEALTH", "").lower() in ("true", "1", "yes"):
    try:
        import undetected_chromedriver as _uc
        logger.info("undetected-chromedriver loaded (stealth mode)")
    except Exception as e:
        logger.warning("BROWSER_STEALTH enabled but undetected-chromedriver unavailable: %s", e)


def _detect_chromium_binary() -> str:
    candidates = [
        "/snap/chromium/current/usr/lib/chromium-browser/chrome",
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    logger.warning("Chromium binary not found via auto-detection")
    return "chromium"


def _detect_chromedriver() -> str:
    env_path = os.environ.get("CHROMEDRIVER_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    candidates = [
        shutil.which("chromedriver"),
        "/snap/chromium/current/usr/lib/chromium-browser/chromedriver",
        "/snap/bin/chromium.chromedriver",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


class SeleniumEngine(BrowserEngine):
    name = "selenium"

    def __init__(self):
        self._driver = None
        self._last_url = ""
        self._temp_dir = None

    def _ensure_driver(self):
        if self._driver is not None:
            try:
                self._driver.current_url
                return
            except WebDriverException:
                logger.warning("Selenium driver session lost, reconnecting...")
                self._driver = None

        remote_url = os.environ.get("SELENIUM_REMOTE_URL")
        if remote_url:
            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            if os.environ.get("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes"):
                opts.add_argument("--headless=new")
            self._driver = webdriver.Remote(command_executor=remote_url, options=opts)
            logger.info("Connected to remote Selenium at %s", remote_url)
            return

        debug_port = os.environ.get("CHROME_DEBUG_PORT")
        debug_host = os.environ.get("CHROME_DEBUG_HOST", "127.0.0.1")
        if debug_port is not None:
            try:
                opts = Options()
                opts.add_experimental_option("debuggerAddress", f"{debug_host}:{debug_port}")
                chromedriver = _detect_chromedriver()
                if chromedriver:
                    self._driver = webdriver.Chrome(service=Service(executable_path=chromedriver), options=opts)
                else:
                    self._driver = webdriver.Chrome(options=opts)
                logger.info("Connected to external Chrome at %s:%s", debug_host, debug_port)
                return
            except Exception as e:
                logger.warning("Failed to connect to external Chrome: %s. Starting new instance.", e)

        window_size = os.environ.get("CHROME_WINDOW_SIZE", "1920,1080")
        lang = os.environ.get("CHROME_LANG", "es-ES")

        opts = Options()
        opts.binary_location = _detect_chromium_binary()
        use_sandbox = os.environ.get("BROWSER_NO_SANDBOX", "").lower() in ("true", "1", "yes")
        if use_sandbox:
            opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")
        if os.environ.get("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes"):
            opts.add_argument("--headless=old")
        opts.add_argument("--remote-debugging-port=0")
        opts.add_argument("--remote-debugging-address=127.0.0.1")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-features=ChromeWhatsNewUI")
        opts.add_argument("--disable-features=TranslateUI")
        if _uc is None:
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
        profile_dir = os.environ.get("CHROME_USER_DATA_DIR")
        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)
            self._temp_dir = profile_dir
        else:
            self._temp_dir = tempfile.mkdtemp(prefix='chromedev-')
        if _uc is None:
            opts.add_argument(f"--user-data-dir={self._temp_dir}")
        opts.add_argument(f"--window-size={window_size}")
        opts.add_argument(f"--lang={lang}")
        opts.add_argument("--disable-search-engine-choice-screen")
        opts.add_argument("--disable-sync")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--no-first-run")
        opts.page_load_strategy = "normal"
        chromedriver = _detect_chromedriver()
        try:
            if _uc is not None:
                self._driver = _uc.Chrome(
                    options=opts, 
                    user_data_dir=self._temp_dir,
                    version_main=int(os.environ.get("CHROME_VERSION", "149"))
                )
            elif chromedriver:
                service = Service(executable_path=chromedriver)
                self._driver = webdriver.Chrome(service=service, options=opts)
            else:
                logger.warning("chromedriver not found via auto-detection, using default")
                self._driver = webdriver.Chrome(options=opts)
            if _uc is None:
                self._disable_automation_flags()
            self._driver.set_page_load_timeout(30)
        except WebDriverException as e:
            logger.error("Failed to start Chrome: %s", e)
            raise

    def _disable_automation_flags(self):
        try:
            self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                """
            })
        except Exception as e:
            logger.debug("Could not disable automation flags: %s", e)

    def _scroll_into_view(self, element):
        try:
            self._driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});",
                element
            )
        except Exception as e:
            logger.debug("scroll_into_view failed: %s", e)

    def _wait_for_page_load(self, timeout=10):
        try:
            WebDriverWait(self._driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            logger.warning("Page did not fully load within %ds", timeout)
        except Exception as e:
            logger.warning("wait_for_page_load exception: %s", e)

    def navigate(self, url: str) -> PageResult:
        try:
            self._ensure_driver()
            self._driver.get(url)
            self._wait_for_page_load()
            self._last_url = self._driver.current_url
            body = self._driver.find_element(By.TAG_NAME, "body")
            text_max = int(os.environ.get("BROWSER_TEXT_MAX", "15000"))
            return PageResult(
                url=self._last_url,
                title=self._driver.title or "",
                html=self._driver.page_source,
                text=body.text[:text_max],
            )
        except Exception as e:
            logger.exception("navigate failed")
            return PageResult(url=url, title="", html="", text="", error=str(e))

    def extract(self, selector: str) -> list[str]:
        try:
            self._ensure_driver()
            elements = self._driver.find_elements(By.CSS_SELECTOR, selector)
            return [el.text.strip() for el in elements if el.text.strip()]
        except Exception:
            logger.exception("extract failed")
            return []

    def get_links(self) -> list[LinkInfo]:
        try:
            self._ensure_driver()
            links = []
            base = self._driver.current_url
            for a in self._driver.find_elements(By.TAG_NAME, "a"):
                href = a.get_attribute("href")
                text = a.text.strip()
                if href:
                    parsed = urlparse(href)
                    is_internal = parsed.netloc == urlparse(base).netloc
                    links.append(LinkInfo(href=href, text=text, is_internal=is_internal))
            return links
        except Exception:
            logger.exception("get_links failed")
            return []

    def get_forms(self) -> list[FormInfo]:
        try:
            self._ensure_driver()
            forms = []
            base_url = self._driver.current_url
            for form_el in self._driver.find_elements(By.TAG_NAME, "form"):
                action = form_el.get_attribute("action") or ""
                if action and not action.startswith(("http://", "https://", "//")):
                    action = urljoin(base_url, action)
                method = (form_el.get_attribute("method") or "get").upper()
                fields = []
                for inp in form_el.find_elements(By.CSS_SELECTOR, "input, textarea, select"):
                    tag = inp.tag_name
                    name = inp.get_attribute("name") or ""
                    type_ = inp.get_attribute("type") or "text"
                    placeholder = inp.get_attribute("placeholder") or ""
                    aria_label = inp.get_attribute("aria-label") or ""
                    title_attr = inp.get_attribute("title") or ""

                    label = ""
                    try:
                        inp_id = inp.get_attribute("id")
                        if inp_id:
                            label = self._driver.execute_script("""
                                var id = arguments[0];
                                var el = document.querySelector('label[for="' + CSS.escape(id) + '"]');
                                if (!el) el = document.querySelector('[id="' + CSS.escape(id) + '"]');
                                if (!el) {
                                    var div = document.querySelector('[class*="field"]');
                                    if (div) el = div.previousElementSibling;
                                }
                                return el ? el.textContent.trim() : '';
                            """, inp_id)
                    except WebDriverException:
                        pass
                    if not label:
                        try:
                            label = self._driver.execute_script("""
                                var el = arguments[0];
                                var div = el.closest('[class*="field"]');
                                if (!div) div = el.parentElement;
                                var prev = div.previousElementSibling;
                                while (prev) {
                                    var txt = (prev.textContent || '').trim();
                                    if (txt && !prev.querySelector('textarea, input, select')) {
                                        return txt;
                                    }
                                    prev = prev.previousElementSibling;
                                }
                                return '';
                            """, inp)
                        except Exception as e:
                            logger.debug("label JS fallback failed: %s", e)
                    if not label:
                        try:
                            parent = inp.find_element(By.XPATH, "..")
                            if parent.tag_name == "label":
                                label = parent.text.strip()
                        except Exception as e:
                            logger.debug("parent label fallback failed: %s", e)
                    if not label and placeholder:
                        label = placeholder
                    if not label and aria_label:
                        label = aria_label
                    if not label and title_attr:
                        label = title_attr
                    required = inp.get_attribute("required") is not None
                    options = []
                    if tag == "select":
                        try:
                            options = [opt.text.strip() for opt in inp.find_elements(By.TAG_NAME, "option") if opt.text.strip()]
                        except Exception as e:
                            logger.debug("select options extraction failed: %s", e)
                    fields.append(FormField(tag=tag, name=name, type=type_,
                                            label=label, required=required, options=options))
                forms.append(FormInfo(action=action, method=method, fields=fields))
            return forms
        except Exception:
            logger.exception("get_forms failed")
            return []

    def screenshot(self) -> bytes | None:
        try:
            self._ensure_driver()
            return self._driver.get_screenshot_as_png()
        except Exception:
            logger.exception("screenshot failed")
            return None

    def click(self, selector: str) -> str:
        try:
            self._ensure_driver()
            el = WebDriverWait(self._driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            self._scroll_into_view(el)
            try:
                el.click()
            except Exception as e:
                logger.debug("click() failed, using JS fallback: %s", e)
                self._driver.execute_script("arguments[0].click();", el)
            self._wait_for_page_load(5)
            return f"Clicked element matching '{selector}'"
        except TimeoutException:
            return f"Element not clickable: '{selector}'"
        except Exception as e:
            logger.exception("click failed")
            return f"Click failed: {e}"

    def click_by_text(self, text: str) -> str:
        try:
            self._ensure_driver()
            script = """
            const texts = arguments[0].split('|');
            const elements = document.querySelectorAll('button, a, input[type=submit], input[type=button], span[role=button], [class*=btn], [class*=button]');
            for (const el of elements) {
                const elText = el.textContent.trim().toLowerCase();
                if (texts.some(t => elText.includes(t.trim().toLowerCase()))) {
                    el.click();
                    return 'Clicked: ' + el.textContent.trim();
                }
            }
            return 'No element found with text: ' + arguments[0];
            """
            result = self._driver.execute_script(script, text)
            self._wait_for_page_load(5)
            return str(result)
        except Exception as e:
            logger.exception("click_by_text failed")
            return f"click_by_text failed: {e}"

    def _validate_script(self, script: str) -> None:
        _BLOCKED_JS_PATTERNS = [
            r"\bfetch\s*\(",
            r"\bxmlhttprequest\b",
            r"\bwebsocket\b",
            r"\bfilereader\b",
            r"\bimportscripts\b",
            r"\bworker\b",
            r"\bnavigator\.sendbeacon\b",
            r"\bdocument\.write\b",
            r"\bdocument\.open\b",
            r"\btop\.",
            r"\bparent\.",
            r"\b(alert|confirm|prompt)\s*\(",
        ]
        dangerous = [
            "eval", "function", "settimeout", "setinterval",
            "new function", "reflect.construct",
            "import(", "importscripts",
        ]
        script_lower = script.lower()
        for keyword in dangerous:
            if keyword in script_lower:
                raise ValueError(f"Script blocked: contains dangerous API '{keyword}'")
        for pattern in _BLOCKED_JS_PATTERNS:
            if re.search(pattern, script_lower):
                raise ValueError("Script blocked: contains dangerous API")

    def run_script(self, script: str) -> str:
        try:
            self._validate_script(script)
            self._ensure_driver()
            result = self._driver.execute_script(script)
            if result is None:
                return "Script executed (no return value)"
            result_str = str(result)
            max_len = int(os.environ.get("BROWSER_TEXT_MAX", "5000"))
            if len(result_str) > max_len:
                result_str = result_str[:max_len] + "..."
            return result_str
        except Exception as e:
            logger.exception("run_script failed")
            return f"run_script failed: {e}"

    def fill(self, selector: str, value: str) -> str:
        try:
            self._ensure_driver()
            el = WebDriverWait(self._driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            self._scroll_into_view(el)
            el.clear()
            js_fill_threshold = int(os.environ.get("BROWSER_JS_FILL_THRESHOLD", "100"))
            if len(value) > js_fill_threshold:
                self._driver.execute_script("""
                    arguments[0].value = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                    arguments[0].dispatchEvent(new Event('change', {bubbles: true}));
                """, el, value)
            else:
                el.send_keys(value)
            return f"Filled '{selector}' with '{value[:50]}{'...' if len(value) > 50 else ''}'"
        except TimeoutException:
            return f"Element not found: '{selector}'"
        except Exception as e:
            logger.exception("fill failed")
            return f"Fill failed: {e}"

    def scroll(self, direction: str = "down") -> str:
        try:
            self._ensure_driver()
            direction = direction.lower()
            valid = {"down", "up", "bottom", "top"}
            if direction not in valid:
                return f"Invalid direction: {direction}. Use: {', '.join(valid)}"
            if direction == "down":
                self._driver.execute_script("window.scrollBy(0, window.innerHeight)")
            elif direction == "up":
                self._driver.execute_script("window.scrollBy(0, -window.innerHeight)")
            elif direction == "bottom":
                self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            elif direction == "top":
                self._driver.execute_script("window.scrollTo(0, 0)")
            return f"Scrolled {direction}"
        except Exception as e:
            logger.exception("scroll failed")
            return f"Scroll failed: {e}"

    def wait(self, ms: int = 1000) -> str:
        time.sleep(ms / 1000)
        return f"Waited {ms}ms"

    def close(self):
        if self._driver is None:
            return
        try:
            self._driver.quit()
        except Exception:
            logger.exception("close failed")
        finally:
            self._driver = None
        if self._temp_dir and not os.environ.get("CHROME_USER_DATA_DIR"):
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = None
