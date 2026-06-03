# Tutorial: MCP Servers — De Cero a Productivo

Una guía práctica para usar los 6 servidores MCP del monorepo con ejemplos reales.

## Índice

1. [¿Qué es MCP?](#qué-es-mcp)
2. [Instalación](#instalación)
3. [Caso 1: Scrapear una web y exportarla a CSV](#caso-1-scrapear-una-web-y-exportarla-a-csv)
4. [Caso 2: Navegador automático para tomar screenshots](#caso-2-navegador-automático-para-tomar-screenshots)
5. [Caso 3: Router de IA multi-provider](#caso-3-router-de-ia-multi-provider)
6. [Caso 4: Procesar PDFs en lote](#caso-4-procesar-pdfs-en-lote)
7. [Caso 5: Pipeline completa (scrape → IA → PDF)](#caso-5-pipeline-completa-scrape--ia--pdf)

---

## ¿Qué es MCP?

MCP (Model Context Protocol) es un protocolo abierto que permite a agentes de IA (como Claude, Gemini, Copilot) comunicarse con herramientas externas. Cada "MCP server" expone herramientas que el agente puede invocar.

Este monorepo agrupa 6 servidores MCP listos para usar.

## Instalación

```bash
pip install medalcode-mcp-servers
```

Esto instala 6 comandos CLI:

| Comando | Servidor |
|---|---|
| `browsermcp` | Automatización de navegador |
| `routemcp` | Router de IA |
| `scrapemcp` | Web scraping |
| `docmcp` | Procesamiento de PDFs |
| `linkedinmcp` | Búsqueda en LinkedIn |
| `pathwise` | Plataforma de carrera |

Cada servidor se ejecuta como un proceso independiente y se comunica via stdio JSON-RPC.

---

## Caso 1: Scrapear una web y exportarla a CSV

Extraer todas las tablas de una página y guardarlas como CSV.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="scrapemcp",
        args=[]
    )

    async with ClientSession(server) as session:
        # 1. Inspeccionar la página
        result = await session.call_tool("inspect", {
            "url": "https://es.wikipedia.org/wiki/Chile"
        })
        print("Meta tags:", result.content)

        # 2. Extraer tablas
        result = await session.call_tool("tables", {
            "url": "https://es.wikipedia.org/wiki/Chile",
            "selector": "table.wikitable"
        })
        print(f"Tablas encontradas: {len(result.content)}")

        # 3. Exportar a CSV
        result = await session.call_tool("export", {
            "data": result.content[0],
            "format": "csv"
        })
        with open("tabla_chile.csv", "w") as f:
            f.write(result.content[0])

asyncio.run(main())
```

**Output:** `tabla_chile.csv` con los datos estructurados.

---

## Caso 2: Navegador automático para tomar screenshots

Usar BrowserMCP para navegar un sitio, tomar captura y extraer links.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="browsermcp",
        args=[],
        env={"BROWSER_ENGINE": "selenium"}
    )

    async with ClientSession(server) as session:
        # Navegar a la página
        result = await session.call_tool("navigate", {
            "url": "https://news.ycombinator.com"
        })
        print(f"Título: {result.content[0].text}")

        # Tomar screenshot
        result = await session.call_tool("screenshot", {})
        with open("screenshot.png", "wb") as f:
            f.write(result.content[0].data)

        # Extraer todos los links
        result = await session.call_tool("links", {})
        links = result.content[0].text
        print(f"Links encontrados: {len(links.split(chr(10)))}")

asyncio.run(main())
```

**Output:** `screenshot.png` + lista de links.

---

## Caso 3: Router de IA multi-provider

Usar RouteMCP para clasificar una tarea y enrutarla al mejor modelo.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="routemcp",
        args=[],
        env={
            "GEMINI_API_KEY": "tu-api-key",
            "GROQ_API_KEY": "tu-api-key"
        }
    )

    async with ClientSession(server) as session:
        # Clasificar tarea
        result = await session.call_tool("classify_task", {
            "prompt": "Escribe una función en Python que ordene una lista"
        })
        print(f"Tipo detectado: {result.content}")

        # Enrutar automáticamente al mejor modelo
        result = await session.call_tool("route", {
            "prompt": "Explica la diferencia entre TCP y UDP en 3 párrafos"
        })
        print(f"Respuesta: {result.content}")

        # Comparar respuestas de 2 modelos
        result = await session.call_tool("compare", {
            "prompt": "solve 2+2",
            "models": "gemini-2.0-flash,llama-3.3-70b"
        })
        print(f"Comparación: {result.content}")

asyncio.run(main())
```

**Output:** Clasificación + respuesta del mejor modelo + comparación.

---

## Caso 4: Procesar PDFs en lote

Leer, mergear y generar reportes con DocMCP.

```python
import asyncio
from mcp import ClientSession, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command="docmcp",
        args=[],
        env={"DOCMCP_WORKDIR": "/home/user/documentos"}
    )

    async with ClientSession(server) as session:
        # Leer un PDF
        result = await session.call_tool("read", {"path": "contrato.pdf"})
        print(f"Texto: {result.content[:500]}...")

        # Generar un reporte
        result = await session.call_tool("generate_report", {
            "title": "Reporte Mensual",
            "content": '{"Ventas": ["Enero: $10k", "Febrero: $12k", "Marzo: $15k"]}',
            "output": "reporte.pdf"
        })

        # Convertir a Markdown
        result = await session.call_tool("to_markdown", {"path": "contrato.pdf"})
        with open("contrato.md", "w") as f:
            f.write(result.content[0].text)

asyncio.run(main())
```

**Output:** `reporte.pdf` generado + `contrato.md` convertido.

---

## Caso 5: Pipeline completa (scrape + IA + PDF)

Combinar ScrapeMCP + RouteMCP + DocMCP en un solo flujo:

1. Scrapear artículos de un blog
2. Resumirlos con IA (RouteMCP)
3. Generar un PDF con los resúmenes

```python
import asyncio, json
from mcp import ClientSession, StdioServerParameters

async def main():
    scrape = StdioServerParameters(command="scrapemcp")
    route = StdioServerParameters(command="routemcp", args=[],
        env={"GEMINI_API_KEY": "tu-api-key"})
    doc = StdioServerParameters(command="docmcp", args=[],
        env={"DOCMCP_WORKDIR": "/tmp"})

    async with ClientSession(scrape) as s1, \
              ClientSession(route) as s2, \
              ClientSession(doc) as s3:

        # 1. Scrapear lista de artículos
        items = await s1.call_tool("scrape_list", {
            "url": "https://example.com/blog",
            "item_selector": "article",
            "fields": {"title": "h2", "date": "time", "excerpt": "p"}
        })
        articulos = json.loads(items.content[0].text)[:3]
        print(f"Artículos encontrados: {len(articulos)}")

        # 2. Resumir cada artículo con IA
        resumenes = []
        for art in articulos:
            resumen = await s2.call_tool("ask", {
                "model": "gemini-2.0-flash",
                "prompt": f"Resume en 2 líneas: {art['title']} - {art['excerpt']}"
            })
            resumenes.append(f"## {art['title']}\n{resumen.content}")

        # 3. Generar PDF con los resúmenes
        contenido = {
            "resumenes": resumenes
        }
        reporte = await s3.call_tool("generate_report", {
            "title": "Blog Roundup - Resúmenes IA",
            "content": json.dumps(contenido),
            "output": "blog_roundup.pdf"
        })
        print(f"PDF generado: blog_roundup.pdf")

asyncio.run(main())
```

**Output:** `blog_roundup.pdf` con artículos scrapeados y resumidos por IA.

---

## Tips y Buenas Prácticas

| Práctica | Detalle |
|---|---|
| Usar `DOCMCP_WORKDIR` | Siempre configura el directorio de trabajo para seguridad |
| Variables de entorno | Las API keys van en entorno, nunca en código |
| Rate limiting | ScrapeMCP tiene protección SSRF integrada |
| Fallback | BrowserMCP falla automático a motor estático si no hay navegador |
| Logging | Todos los servidores logean en stderr, no interfieren con MCP |

## Siguientes pasos

- Revisa los [good first issues](https://github.com/Medalcode/mcp-servers/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
- Explora cada servidor en `/servers/`
- Combina servidores para crear pipelines complejos
