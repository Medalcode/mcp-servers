#!/bin/bash
REPO="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$REPO:$PYTHONPATH"

source /tmp/mcp-venv/bin/activate

load_env() {
  if [ -f "$REPO/.env" ]; then
    export GITHUB_TOKEN="$(grep GITHUB_TOKEN "$REPO/.env" 2>/dev/null | cut -d= -f2)"
    export ALLOWED_PATH="$HOME"
    export $(grep -v '^\s*#' "$REPO/.env" | xargs -d '\n' 2>/dev/null)
  fi
}
load_env

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
  nohup bash -c "cd '$REPO' && source /tmp/mcp-venv/bin/activate && PYTHONPATH='$REPO:\$PYTHONPATH' python '/tmp/run_${name}.py'" > "/tmp/${name}_mcp.log" 2>&1 &
  disown
  echo "  $name -> :$port"
}

echo "Iniciando todos los MCP servers..."
echo ""

start_server "browser"      8001 "servers.browser"
start_server "route"        8002 "servers.route"
start_server "scrape"       8003 "servers.scrape"
start_server "doc"          8004 "servers.doc"
start_server "linkedin"     8005 "servers.linkedin"
start_server "pathwise"     8006 "servers.pathwise"
start_server "github_mcp"   8007 "servers.github_mcp"
start_server "filesystem"   8008 "filesystem_server"
start_server "memory"       8009 "servers.memory"
start_server "database"     8010 "servers.database_mcp"
start_server "email"        8011 "servers.email_mcp"
start_server "task_tracker" 8012 "servers.task_tracker"
# graphify uses its own serve_http(), not FastMCP.sse_app()
nohup bash -c "cd '$REPO' && source /tmp/mcp-venv/bin/activate && PYTHONPATH='$REPO:\$PYTHONPATH' MCP_PORT=8013 MCP_HOST=0.0.0.0 python -c 'from servers.graphify_wrapper import main; main()'" > /tmp/graphify_mcp.log 2>&1 &
disown
echo "  graphify -> :8013"

sleep 3
echo ""
echo "Verificando..."
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012 8013; do
  if ss -tlnp 2>/dev/null | grep -q ":$port"; then
    echo "  $port activo"
  else
    echo "  $port caido"
  fi
done
echo ""
echo "Logs: /tmp/*_mcp.log"
