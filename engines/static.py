import re
import os
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

from engines.base import BrowserEngine, PageResult, LinkInfo, FormInfo, FormField


class StaticEngine(BrowserEngine):
    name = "static"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; BrowserMCP/1.0)",
        })
        self._soup: BeautifulSoup | None = None
        self._current_url: str = ""

    def navigate(self, url: str) -> PageResult:
        try:
            resp = self._session.get(url, timeout=(5, 15))
            resp.raise_for_status()
            self._current_url = resp.url
            content_type = resp.headers.get("content-type", "")
            if "html" not in content_type:
                return PageResult(
                    url=self._current_url,
                    title="",
                    html="",
                    text=resp.text[:5000],
                    error=f"Not HTML (content-type: {content_type})",
                )
            self._soup = BeautifulSoup(resp.content, "lxml")
            if self._soup.title and self._soup.title.string:
                title = self._soup.title.string.strip()
            else:
                title = ""
            text = self._soup.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text)
            text_max = int(os.environ.get("BROWSER_TEXT_MAX", "15000"))
            return PageResult(
                url=self._current_url,
                title=title,
                html=str(self._soup),
                text=text[:text_max],
            )
        except requests.RequestException as e:
            return PageResult(
                url=url,
                title="",
                html="",
                text="",
                error=str(e),
            )

    def extract(self, selector: str) -> list[str]:
        if not self._soup:
            return []
        elements = self._soup.select(selector)
        return [el.get_text(strip=True) for el in elements]

    def get_links(self) -> list[LinkInfo]:
        if not self._soup:
            return []
        links = []
        base = self._current_url
        for a in self._soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            full = urljoin(base, href)
            parsed = urlparse(full)
            is_internal = parsed.netloc == urlparse(base).netloc
            links.append(LinkInfo(href=full, text=text, is_internal=is_internal))
        return links

    def get_forms(self) -> list[FormInfo]:
        if not self._soup:
            return []
        forms = []
        for form in self._soup.find_all("form"):
            action = form.get("action", "")
            method = form.get("method", "get").upper()
            fields = []
            for inp in form.find_all(["input", "textarea", "select"]):
                tag = inp.name
                name = inp.get("name", "")
                type_ = inp.get("type", "text") if tag == "input" else tag
                label_el = form.find("label", attrs={"for": inp.get("id", "")})
                label = label_.get_text(strip=True) if label_el else ""
                if not label:
                    parent_label = inp.find_parent("label")
                    if parent_label:
                        label = parent_label.get_text(strip=True)
                required = inp.get("required") is not None
                fields.append(FormField(
                    tag=tag, name=name, type=type_, label=label, required=required,
                ))
            forms.append(FormInfo(action=action, method=method, fields=fields))
        return forms

    def screenshot(self) -> bytes | None:
        return None

    def click(self, selector: str) -> str:
        return "Click requires a browser engine (Selenium or Playwright)"

    def fill(self, selector: str, value: str) -> str:
        return "Form filling requires a browser engine (Selenium or Playwright)"

    def click_by_text(self, text: str) -> str:
        return "Click by text requires a browser engine (Selenium or Playwright)"

    def run_script(self, script: str) -> str:
        return "JavaScript execution requires a browser engine (Selenium or Playwright)"

    def scroll(self, direction: str) -> str:
        return "Scrolling requires a browser engine (Selenium or Playwright)"

    def wait(self, ms: int) -> str:
        return "Waiting requires a browser engine (Selenium or Playwright)"

    def close(self):
        self._session.close()
