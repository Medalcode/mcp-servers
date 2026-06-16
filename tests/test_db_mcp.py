import pytest
import tempfile
import sqlite3
from db_mcp.engine import query_sqlite, list_sqlite_tables, describe_sqlite_table


@pytest.mark.asyncio
async def test_query_sqlite():
    tmp = tempfile.mktemp(suffix=".db")
    with sqlite3.connect(tmp) as conn:
        conn.execute("CREATE TABLE test (id INT, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        conn.commit()
    result = await query_sqlite(tmp, "SELECT * FROM test")
    assert "1" in result
    assert "hello" in result


@pytest.mark.asyncio
async def test_list_sqlite_tables():
    tmp = tempfile.mktemp(suffix=".db")
    with sqlite3.connect(tmp) as conn:
        conn.execute("CREATE TABLE foo (id INT)")
        conn.execute("CREATE TABLE bar (id INT)")
        conn.commit()
    result = await list_sqlite_tables(tmp)
    assert "foo" in result
    assert "bar" in result


@pytest.mark.asyncio
async def test_describe_sqlite_table():
    tmp = tempfile.mktemp(suffix=".db")
    with sqlite3.connect(tmp) as conn:
        conn.execute("CREATE TABLE t (id INT PRIMARY KEY, name TEXT NOT NULL)")
        conn.commit()
    result = await describe_sqlite_table(tmp, "t")
    assert "id" in result
    assert "name" in result
    assert "PRIMARY" in result or "\U0001f511" in result
