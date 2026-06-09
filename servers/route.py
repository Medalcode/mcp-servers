from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from router.engine import RouterEngine
from router.models import MODELS, TASK_ROUTING
from router.classifier import classify

mcp = FastMCP("RouteMCP")
engine = RouterEngine()


@mcp.tool()
async def route(prompt: str, task_type: str = "") -> str:
    tt = task_type if task_type else None
    try:
        return await engine.route(prompt, tt)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def ask(model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 8192) -> str:
    available = []
    for m in MODELS:
        prov = engine.providers.get(m.provider)
        if prov and await prov.is_available():
            available.append(m)
    valid_ids = [m.id for m in available]
    if model not in valid_ids:
        available_str = ", ".join(valid_ids) if valid_ids else "none (no API keys configured)"
        if not valid_ids:
            return (f"Model '{model}' not available. Configure API keys via:\n"
                    f"  GEMINI_API_KEY, GROQ_API_KEY, CEREBRAS_API_KEY\n"
                    f"Available models: none")
        return f"Model '{model}' not found. Available: {available_str}"
    try:
        return await engine.ask(model, prompt, temperature=temperature, max_tokens=max_tokens)
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def compare(prompt: str, models: str, temperature: float = 0.7, max_tokens: int = 8192) -> str:
    model_list = [m.strip() for m in models.split(",")]
    try:
        results = await engine.compare(prompt, model_list, temperature=temperature, max_tokens=max_tokens)
        return "\n\n".join(
            f"=== {mid} ===\n{res}"
            for mid, res in results.items()
        )
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
async def models() -> str:
    available = await engine.get_available_models()
    if not available:
        return ("No models available. Configure API keys as environment variables:\n"
                "  GEMINI_API_KEY=<key>\n"
                "  GROQ_API_KEY=<key>\n"
                "  CEREBRAS_API_KEY=<key>")
    lines = ["# Available Models", ""]
    for m in available:
        strengths = ", ".join(m.strengths)
        lines.append(f"## {m.id}")
        lines.append(f"  Provider: {m.provider}")
        lines.append(f"  Name: {m.name}")
        lines.append(f"  Strengths: {strengths}")
        lines.append(f"  Context: {m.context_window:,} tokens")
        lines.append(f"  Speed: {m.speed}")
        lines.append(f"  Cost: {m.cost}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool()
async def classify_task(prompt: str) -> str:
    task = await classify(prompt)
    recommended = TASK_ROUTING.get(task, TASK_ROUTING["general"])
    return (
        f"Detected task type: {task}\n"
        f"Recommended models: {', '.join(recommended)}"
    )


def main():
    import os
    load_dotenv()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        mcp.run(transport="sse", host=os.environ.get("MCP_HOST", "0.0.0.0"), port=int(os.environ.get("MCP_PORT", "8080")))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
