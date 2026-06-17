#!/usr/bin/env python3
"""Local agent — Ollama + tools (bash, read, web)."""
import json, sys, subprocess, re
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "llama3.1:8b"

TOOLS_DESC = """Available tools:
- bash({"command": "..."})
- read({"path": "..."})
- webfetch({"url": "..."})
"""

SYSTEM = f"""Eres un agente que ejecuta tareas. Tienes estas herramientas:
{TOOLS_DESC}
Reglas:
- Para usar una herramienta, responde SOLO con el JSON de la llamada.
- Ejemplo: {{"tool": "bash", "args": {{"command": "ls"}}}}
- Después de recibir el resultado, puedes llamar otra herramienta o dar la respuesta final.
- Cuando termines, responde sin JSON.
- Responde en el mismo idioma del usuario."""

def run_tool(name, args):
    if name == "bash":
        r = subprocess.run(args["command"], shell=True, capture_output=True, text=True, timeout=30)
        return (r.stdout or r.stderr or "(sin output)")[:4000]
    if name == "read":
        with open(args["path"]) as f:
            return f.read()[:4000]
    if name == "webfetch":
        import httpx
        return httpx.get(args["url"], timeout=15).text[:4000]
    return f"Error: tool '{name}' no existe"

def parse_tool_call(text):
    m = re.search(r'\{\s*"tool"\s*:\s*"(\w+)"\s*,\s*"args"\s*:\s*(\{.*?\})\s*\}', text, re.DOTALL)
    if m:
        return m.group(1), json.loads(m.group(2))
    m2 = re.search(r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:\s*(\{.*?\})\s*\}', text, re.DOTALL)
    if m2:
        return m2.group(1), json.loads(m2.group(2))
    return None, None

def run(prompt):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]
    for step in range(10):
        resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.1)
        content = resp.choices[0].message.content or ""
        
        name, args = parse_tool_call(content)
        if name:
            print(f"  → {name}({json.dumps(args)[:100]})")
            result = run_tool(name, args)
            messages.append({"role": "user", "content": f"Resultado: {result}\n\nContinúa o da la respuesta final."})
        else:
            print(content)
            return
    print("(máximo de pasos alcanzado)")

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("> ")
    run(prompt)
