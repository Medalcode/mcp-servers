import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.browser_client import call_tool, stop_browser, ensure_browser

# Cargar variables de entorno desde el archivo .env
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    print("Error: EMAIL y PASSWORD deben estar definidos en un archivo .env o en las variables de entorno.")
    sys.exit(1)

async def safe(tool, args=None):
    r = await call_tool(tool, args or {})
    if not r or r.startswith("BrowserMCP failed"):
        return ""
    return r

async def apply_to_portal(portal: str):
    print(f"\n=== Iniciando flujo de aplicación para {portal.upper()} ===")
    
    # Asegurar que el navegador está corriendo
    browser_ok = await ensure_browser()
    if not browser_ok:
        print("No se pudo iniciar el navegador MCP.")
        return
        
    try:
        if portal.lower() == "trabajando":
            # Flow para trabajando
            await safe("navigate", {"url": "https://www.trabajando.cl/ingresa-a-tu-cuenta"})
            await asyncio.sleep(4)
            print("  Intentando login...")
            await safe("fill", {"selector": "input[name='email']", "value": EMAIL})
            # Completar lógica según aplique...
            
        elif portal.lower() == "firstjob":
            # Flow para firstjob
            await safe("navigate", {"url": "https://firstjob.me/login"})
            await asyncio.sleep(4)
            print("  Intentando login...")
            await safe("fill", {"selector": "input[name='email']", "value": EMAIL})
            # Completar lógica según aplique...
            
        else:
            print(f"Portal '{portal}' no está implementado en este script.")
            
    finally:
        await stop_browser()
        print(f"=== Flujo finalizado para {portal.upper()} ===")


def main():
    parser = argparse.ArgumentParser(description="Script unificado de aplicación automática")
    parser.add_argument("portal", type=str, help="Portal a procesar (ej. trabajando, firstjob)")
    
    args = parser.parse_args()
    
    asyncio.run(apply_to_portal(args.portal))

if __name__ == "__main__":
    main()
