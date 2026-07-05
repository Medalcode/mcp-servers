#!/bin/bash
# Inicia todos los MCP servers localmente (sin Docker)
VENV=/tmp/mcp-venv
REPO="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$REPO:$PYTHONPATH"
export GITHUB_TOKEN="$(grep GITHUB_TOKEN "$REPO/.env" 2>/dev/null | cut -d= -f2)"
export ALLOWED_PATH="$HOME"

start_server() {
  local name=$1 port=$2 module=$3
  cat > "/tmp/run_${name}.py" << PYEOF
import os, sys
sys.path.insert(0, "$REPO")
from dotenv import load_dotenv
load_dotenv()
import importlib
mod = importlib.import_module("$module")
import uvicorn
app = mod.mcp.sse_app()
uvicorn.run(app, host="0.0.0.0", port=$port, log_level="warning")
PYEOF
  nohup bash -c "cd '$REPO' && source '$VENV/bin/activate' && PYTHONPATH='$REPO:\$PYTHONPATH' ALLOWED_PATH='$ALLOWED_PATH' GITHUB_TOKEN='$GITHUB_TOKEN' python '/tmp/run_${name}.py'" > "/tmp/${name}_mcp.log" 2>&1 &
  disown
  echo "  ✅ $name -> :$port"
}

source "$VENV/bin/activate"
echo "Iniciando MCP servers..."
start_server "route"       8002 "servers.route"
start_server "github_mcp"  8007 "servers.github_mcp"
start_server "filesystem"  8008 "filesystem_server"
start_server "memory"      8009 "servers.memory"
start_server "database"    8010 "servers.database_mcp"
start_server "email"       8011 "servers.email_mcp"
start_server "task_tracker" 8012 "servers.task_tracker"
sleep 2
echo ""
echo "Verificando..."
for port in 8002 8007 8008 8009 8010 8011 8012; do
  if ss -tlnp 2>/dev/null | grep -q ":$port"; then
    echo "  ✅ Puerto $port activo"
  else
    echo "  ❌ Puerto $port caido"
  fi
done
echo ""
echo "Logs: /tmp/*_mcp.log"
