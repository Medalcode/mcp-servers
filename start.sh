#!/bin/bash
cd "$(dirname "$0")"

echo "==========================================="
echo "Iniciando Pathwise..."
echo "==========================================="

# Usar uv run para asegurar que use el entorno virtual correcto con todas las dependencias
/home/medalcode/.local/bin/uv run uvicorn api_server:app --host 0.0.0.0 --port 8010 &
SERVER_PID=$!

sleep 2

# Check if the process is still running after 2 seconds
if kill -0 $SERVER_PID 2>/dev/null; then
    xdg-open "http://localhost:8010"
    echo "Servidor corriendo en http://localhost:8010"
    echo "Cierra esta ventana o presiona Ctrl+C para detener el servidor y salir."
    wait $SERVER_PID
else
    echo "==========================================="
    echo "ERROR: El servidor se ha cerrado inesperadamente durante el arranque."
    echo "Revisa los mensajes de arriba para ver qué falló."
    echo "==========================================="
fi

echo ""
echo "El proceso ha terminado."
read -p "Presiona Enter para cerrar esta ventana..."
