import asyncio


from router.models import MODELS, TASK_ROUTING, ModelInfo
from router.classifier import classify
from router.providers.google_provider import GoogleProvider
from router.providers.groq_provider import GroqProvider
from router.providers.cerebras_provider import CerebrasProvider
from router.providers.ollama_provider import OllamaProvider
from router.providers.base import ProviderError


class RouterEngine:
    def __init__(self):
        self._providers = {}
        self._provider_classes = {
            "google": GoogleProvider,
            "groq": GroqProvider,
            "cerebras": CerebrasProvider,
            "ollama": OllamaProvider,
        }

    def _get_provider(self, name: str):
        if name not in self._providers:
            cls = self._provider_classes.get(name)
            if cls:
                self._providers[name] = cls()
        return self._providers.get(name)

    @property
    def providers(self) -> dict:
        for name in self._provider_classes:
            self._get_provider(name)
        return self._providers

    async def get_available_models(self) -> list[ModelInfo]:
        available = []
        for m in MODELS:
            prov = self._get_provider(m.provider)
            if prov and await prov.is_available():
                available.append(m)
        return available

    async def route(self, prompt: str, task_type: str | None = None) -> str:
        task = await classify(prompt, task_type)
        preferences = TASK_ROUTING.get(task, TASK_ROUTING["general"])
        errors = []
        for model_id in preferences:
            model = next((m for m in MODELS if m.id == model_id), None)
            if not model:
                continue
            prov = self._get_provider(model.provider)
            if not prov or not await prov.is_available():
                continue
            try:
                result = await prov.ask(model_id, prompt)
                return result
            except ProviderError as e:
                errors.append(str(e))
                continue
        raise ProviderError("router", f"No models available. Errors: {'; '.join(errors) if errors else 'all providers unavailable'}")

    async def ask(self, model_id: str, prompt: str, temperature: float = 0.7, max_tokens: int = 8192) -> str:
        model = next((m for m in MODELS if m.id == model_id), None)
        if not model:
            raise ProviderError("router", f"Unknown model: {model_id}")
        prov = self._get_provider(model.provider)
        if not prov:
            raise ProviderError("router", f"Unknown provider: {model.provider}")
        if model.provider != prov.name:
            raise ProviderError("router", f"Model '{model_id}' does not belong to provider '{prov.name}'")
        if not await prov.is_available():
            raise ProviderError(model.provider, "Provider not available (API key missing)")
        return await prov.ask(model_id, prompt, temperature=temperature, max_tokens=max_tokens)

    async def compare(self, prompt: str, model_ids: list[str], temperature: float = 0.7, max_tokens: int = 8192) -> dict[str, str]:
        async def fetch(mid: str):
            try:
                res = await self.ask(mid, prompt, temperature=temperature, max_tokens=max_tokens)
                return mid, res
            except ProviderError as e:
                return mid, f"ERROR: {e}"

        tasks = [fetch(mid) for mid in model_ids]
        completed = await asyncio.wait_for(asyncio.gather(*tasks), timeout=120)
        return dict(completed)
