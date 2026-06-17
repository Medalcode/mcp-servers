#!/bin/bash
echo "==========================================="
echo "Iniciando Pathwise Dashboard..."
echo "==========================================="

# Dirigirse al directorio del script
cd "$(dirname "$0")"

# Ejecutar Uvicorn en el puerto 8010
echo "El servidor estará disponible en: http://localhost:8010"
uvicorn api_server:app --host 0.0.0.0 --port 8010
