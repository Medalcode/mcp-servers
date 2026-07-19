import os
import sys

from graphify.serve import serve_http


def main():
    workspace = os.environ.get("GRAPHIFY_WORKDIR", os.getcwd())
    graph_path = os.path.join(workspace, "graphify-out", "graph.json")

    if len(sys.argv) > 1:
        graph_path = sys.argv[1]

    port = int(os.environ.get("MCP_PORT", "8013"))
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    path = os.environ.get("MCP_PATH", "/mcp")

    print(f"graphify MCP on http://{host}:{port}{path}  graph={graph_path}", file=sys.stderr)

    serve_http(graph_path, host=host, port=port, path=path)


if __name__ == "__main__":
    main()
