import sqlite3
from pathlib import Path
from typing import Any

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


def _get_sqlite_conn(path: str) -> tuple[sqlite3.Connection, str]:
    resolved = Path(path).expanduser().resolve()
    conn = sqlite3.connect(str(resolved))
    conn.row_factory = sqlite3.Row
    return conn, str(resolved)


def _get_duckdb_conn(path: str = ":memory:") -> Any:
    if not HAS_DUCKDB:
        raise ImportError("DuckDB not installed. Run: pip install duckdb")
    if path == ":memory:":
        return duckdb.connect(":memory:")
    resolved = Path(path).expanduser().resolve()
    return duckdb.connect(str(resolved))


def _format_results(columns: list[str], rows: list[tuple]) -> str:
    if not rows:
        return "Query returned 0 rows"
    col_widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val or "")))
    header = " | ".join(c.ljust(w) for c, w in zip(columns, col_widths))
    sep = "-+-".join("-" * w for w in col_widths)
    lines = [header, sep]
    for row in rows:
        lines.append(" | ".join(str(v or "").ljust(w) for v, w in zip(row, col_widths)))
    lines.append(f"\n({len(rows)} rows)")
    return "\n".join(lines)


async def query_sqlite(path: str, sql: str) -> str:
    try:
        conn, resolved = _get_sqlite_conn(path)
        cur = conn.execute(sql)
        if sql.strip().upper().startswith(("SELECT", "PRAGMA", "WITH", "EXPLAIN")):
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
            result = _format_results(columns, [tuple(r) for r in rows])
        else:
            conn.commit()
            result = f"Executed OK ({cur.rowcount} rows affected)"
        conn.close()
        return f"Database: {resolved}\n\n{result}"
    except Exception as e:
        return f"SQLite error: {e}"


async def query_duckdb(path: str, sql: str) -> str:
    try:
        conn = _get_duckdb_conn(path)
        result = conn.execute(sql)
        if sql.strip().upper().startswith(("SELECT", "WITH", "EXPLAIN", "DESCRIBE", "SHOW")):
            columns = [d[0] for d in result.description]
            rows = result.fetchall()
            formatted = _format_results(columns, rows)
        else:
            formatted = f"Executed OK ({result.rowcount} rows affected)"
        conn.close()
        db_name = path or ":memory:"
        return f"Database: {db_name}\n\n{formatted}"
    except Exception as e:
        return f"DuckDB error: {e}"


async def list_sqlite_tables(path: str) -> str:
    try:
        conn, resolved = _get_sqlite_conn(path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            conn.close()
            return f"No tables found in {resolved}"
        lines = [f"# Tables — {resolved}", ""]
        for t in tables:
            count = conn.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0]
            lines.append(f"- {t} ({count} rows)")
        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


async def describe_sqlite_table(path: str, table: str) -> str:
    try:
        conn, resolved = _get_sqlite_conn(path)
        cur = conn.execute(f"PRAGMA table_info(\"{table}\")")
        cols = cur.fetchall()
        if not cols:
            conn.close()
            return f"Table '{table}' not found"
        lines = [f"# {table} — {resolved}", ""]
        for c in cols:
            pk = "🔑" if c[5] else " "
            nn = " NOT NULL" if c[3] else ""
            default = f" DEFAULT {c[4]}" if c[4] is not None else ""
            lines.append(f"  {pk} {c[1]} ({c[2]}){nn}{default}")
        count = conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()[0]
        lines.append(f"\n{count} rows total")
        conn.close()
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


async def list_duckdb_tables(path: str = ":memory:") -> str:
    if not HAS_DUCKDB:
        return "Error: DuckDB not installed"
    try:
        conn = _get_duckdb_conn(path)
        result = conn.execute(
            "SELECT table_name, (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as cols FROM information_schema.tables t WHERE table_schema = 'main'"
        )
        tables = result.fetchall()
        conn.close()
        if not tables:
            return "No tables found"
        db_name = path or ":memory:"
        lines = [f"# Tables — {db_name}", ""]
        for t, cols in tables:
            lines.append(f"- {t} ({cols} columns)")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"
