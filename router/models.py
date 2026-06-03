import json
import os
from dataclasses import dataclass, asdict

@dataclass
class ModelInfo:
    id: str
    provider: str
    name: str
    strengths: list[str]
    context_window: int
    speed: str
    cost: str
    is_default: bool = False

_DEFAULT_MODELS = [
    ModelInfo(
        id="gemini-2.5-pro",
        provider="google",
        name="Gemini 2.5 Pro",
        strengths=["reasoning", "math", "code", "long_context", "vision"],
        context_window=1_048_576,
        speed="medium",
        cost="medium",
        is_default=True,
    ),
    ModelInfo(
        id="gemini-2.0-flash",
        provider="google",
        name="Gemini 2.0 Flash",
        strengths=["general", "creative", "vision", "multilingual"],
        context_window=1_048_576,
        speed="fast",
        cost="low",
    ),
    ModelInfo(
        id="gemini-2.5-flash",
        provider="google",
        name="Gemini 2.5 Flash",
        strengths=["reasoning", "code", "general", "vision"],
        context_window=1_048_576,
        speed="fast",
        cost="low",
    ),
    ModelInfo(
        id="gemini-3-flash-preview",
        provider="google",
        name="Gemini 3 Flash Preview",
        strengths=["general", "creative", "vision", "reasoning"],
        context_window=1_048_576,
        speed="fast",
        cost="low",
    ),
    ModelInfo(
        id="llama-3.3-70b",
        provider="groq",
        name="Llama 3.3 70B",
        strengths=["code", "reasoning", "general"],
        context_window=131_072,
        speed="very_fast",
        cost="free",
    ),
    ModelInfo(
        id="mixtral-8x7b",
        provider="groq",
        name="Mixtral 8x7B",
        strengths=["general", "creative", "multilingual"],
        context_window=32_768,
        speed="very_fast",
        cost="free",
    ),
    ModelInfo(
        id="llama-3.1-8b",
        provider="groq",
        name="Llama 3.1 8B",
        strengths=["speed", "simple", "general"],
        context_window=131_072,
        speed="fastest",
        cost="free",
    ),
    ModelInfo(
        id="cerebras-llama-3.3-70b",
        provider="cerebras",
        name="Cerebras Llama 3.3 70B",
        strengths=["speed", "code", "reasoning", "general"],
        context_window=8_192,
        speed="very_fast",
        cost="low",
    ),
]

_DEFAULT_TASK_ROUTING = {
    "code": ["gemini-2.5-pro", "llama-3.3-70b", "gemini-2.5-flash", "cerebras-llama-3.3-70b"],
    "reasoning": ["gemini-2.5-pro", "llama-3.3-70b", "gemini-2.5-flash"],
    "math": ["gemini-2.5-pro", "gemini-2.5-flash", "llama-3.3-70b"],
    "creative": ["gemini-2.0-flash", "gemini-3-flash-preview", "mixtral-8x7b"],
    "general": ["gemini-2.0-flash", "gemini-2.5-flash", "llama-3.3-70b", "gemini-3-flash-preview"],
    "vision": ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"],
    "long_context": ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-3-flash-preview"],
    "speed": ["llama-3.1-8b", "cerebras-llama-3.3-70b", "llama-3.3-70b", "gemini-2.0-flash"],
    "multilingual": ["gemini-2.0-flash", "mixtral-8x7b", "gemini-2.5-flash"],
}

_DEFAULT_TASK_KEYWORDS = {
    "code": ["code", "código", "programa", "función", "función", "script", "api", "bug", "error",
             "debug", "implement", "refactor", "clase", "método", "function", "class",
             "typescript", "python", "javascript", "rust", "go", "html", "css", "sql",
             "algoritmo", "algorithm", "data structure", "estructura de datos"],
    "math": ["math", "matemática", "calcular", "calculate", "equation", "ecuación",
             "sum", "suma", "product", "derivative", "integral", "solve", "resolver",
             "probability", "probabilidad", "statistics", "estadística", "número",
             "formula", "fórmula", "proof", "demostración"],
    "reasoning": ["why", "por qué", "explain", "explica", "reason", "razo", "logic",
                  "lógica", "analyze", "analiza", "compare", "compara", "contrast",
                  "implication", "consecuencia", "cause", "causa", "effect", "efecto",
                  "hypothesis", "hipótesis", "deduce", "think step by step"],
    "creative": ["write", "escribe", "story", "historia", "poem", "poema", "creative",
                 "creativo", "essay", "ensayo", "blog", "article", "artículo", "title",
                 "name", "nombre", "slogan", "lema", "metaphor", "metáfora", "describe",
                 "imagine", "imagina", "draft", "borrador"],
    "vision": ["image", "imagen", "picture", "foto", "photo", "screenshot", "captura",
               "see", "ver", "look", "mirar", "describe this", "what do you see",
               "diagram", "gráfico", "chart", "figure", "figura"],
    "long_context": ["long document", "documento largo", "book", "libro", "novel",
                     "whole file", "todo el archivo", "entire codebase"],
    "multilingual": ["translate", "traduce", "traducción", "translation", "idioma",
                     "language", "español", "english", "português", "français"],
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "models": [asdict(m) for m in _DEFAULT_MODELS],
            "task_routing": _DEFAULT_TASK_ROUTING,
            "task_keywords": _DEFAULT_TASK_KEYWORDS,
        }
        try:
            tmp_path = CONFIG_PATH + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, CONFIG_PATH)
        except Exception:
            pass
        return _DEFAULT_MODELS, _DEFAULT_TASK_ROUTING, _DEFAULT_TASK_KEYWORDS

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        models = [ModelInfo(**m) for m in data.get("models", [])]
        if not models:
            models = _DEFAULT_MODELS

        task_routing = data.get("task_routing", _DEFAULT_TASK_ROUTING)
        task_keywords = data.get("task_keywords", _DEFAULT_TASK_KEYWORDS)
        return models, task_routing, task_keywords
    except Exception:
        return _DEFAULT_MODELS, _DEFAULT_TASK_ROUTING, _DEFAULT_TASK_KEYWORDS

MODELS, TASK_ROUTING, TASK_KEYWORDS = load_config()
