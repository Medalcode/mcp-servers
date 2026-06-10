import os
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from db_mcp.engine import (
    query_sqlite, query_duckdb, list_sqlite_tables,
    describe_sqlite_table, list_duckdb_tables,
)

mcp = FastMCP("DatabaseMCP")


@mcp.tool()
async def sqlite_query(path: str, sql: str) -> str:
    return await query_sqlite(path, sql)


@mcp.tool()
async def sqlite_tables(path: str) -> str:
    return await list_sqlite_tables(path)


@mcp.tool()
async def sqlite_describe(path: str, table: str) -> str:
    return await describe_sqlite_table(path, table)


@mcp.tool()
async def duckdb_query(path: str = ":memory:", sql: str = "") -> str:
    return await query_duckdb(path, sql)


@mcp.tool()
async def duckdb_tables(path: str = ":memory:") -> str:
    return await list_duckdb_tables(path)


def main():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(env_path)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
