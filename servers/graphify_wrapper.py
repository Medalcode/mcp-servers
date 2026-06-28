import os
import sys

def main():
    # El puerto lo maneja el docker-compose si es necesario, 
    # pero graphify --mcp levanta el servidor stdio por defecto.
    # Si queremos usar SSE, verificamos las variables de entorno,
    # aunque la herramienta Graphify maneja la inicialización.
    
    workspace_dir = os.environ.get("GRAPHIFY_WORKDIR", "/workspace")
    
    # Delegamos el control completo al comando de graphify
    print(f"Iniciando Graphify MCP en el directorio: {workspace_dir}", file=sys.stderr)
    
    # Ejecutamos graphify directamente.
    os.execvp("graphify", ["graphify", workspace_dir, "--mcp"])

if __name__ == "__main__":
    main()
