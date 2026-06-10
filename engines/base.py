from abc import ABC, abstractmethod
from dataclasses import dataclass, field



@dataclass
class PageResult:
    url: str
    title: str
    html: str
    text: str
    screenshot: bytes | None = None
    error: str | None = None


@dataclass
class LinkInfo:
    href: str
    text: str
    is_internal: bool = False


@dataclass
class FormField:
    tag: str
    name: str
    type: str
    label: str
    required: bool = False
    options: list[str] = field(default_factory=list)


@dataclass
class FormInfo:
    action: str
    method: str
    fields: list[FormField] = field(default_factory=list)


class BrowserEngine(ABC):

    @abstractmethod
    def navigate(self, url: str) -> PageResult:
        ...

    @abstractmethod
    def extract(self, selector: str) -> list[str]:
        ...

    @abstractmethod
    def get_links(self) -> list[LinkInfo]:
        ...

    @abstractmethod
    def get_forms(self) -> list[FormInfo]:
        ...

    @abstractmethod
    def screenshot(self) -> bytes | None:
        ...

    @abstractmethod
    def click(self, selector: str) -> str:
        ...

    @abstractmethod
    def click_by_text(self, text: str) -> str:
        ...

    @abstractmethod
    def run_script(self, script: str) -> str:
        ...

    @abstractmethod
    def fill(self, selector: str, value: str) -> str:
        ...

    @abstractmethod
    def scroll(self, direction: str) -> str:
        ...

    @abstractmethod
    def wait(self, ms: int) -> str:
        ...

    @abstractmethod
    def close(self) -> None:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
