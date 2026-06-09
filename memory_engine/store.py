import sqlite3
import json
import os
import time
from pathlib import Path
from typing import Any

def _ensure_db():
    memory_dir = Path(os.getenv("MEDALCODE_MEMORY_DIR", str(Path.home() / ".medalcode" / "memory")))
    db_path = memory_dir / "knowledge.db"
    memory_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            tags TEXT DEFAULT '[]',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
    conn.commit()
    return conn


def remember(key: str, value: Any, category: str = "general", tags: list[str] | None = None) -> str:
    conn = _ensure_db()
    now = time.time()
    serialized = json.dumps(value) if not isinstance(value, str) else value
    tags_json = json.dumps(tags or [])
    conn.execute("""
        INSERT INTO memories (key, value, category, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            category = excluded.category,
            tags = excluded.tags,
            updated_at = excluded.updated_at
    """, (key, serialized, category, tags_json, now, now))
    conn.commit()
    conn.close()
    return f"Stored '{key}' in category '{category}'"


def recall(key: str) -> str:
    conn = _ensure_db()
    cur = conn.execute("SELECT value, category, tags, updated_at FROM memories WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return f"No memory found for key '{key}'"
    value, category, tags, updated = row
    try:
        parsed = json.loads(value)
        display = json.dumps(parsed, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        display = value
    tags_list = json.loads(tags)
    return f"Category: {category}\nTags: {', '.join(tags_list)}\nLast updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(updated))}\n\n{display}"


def search(query: str, category: str = "") -> str:
    conn = _ensure_db()
    like = f"%{query}%"
    if category:
        cur = conn.execute(
            "SELECT key, value, category, tags FROM memories WHERE (key LIKE ? OR value LIKE ?) AND category = ? ORDER BY updated_at DESC LIMIT 20",
            (like, like, category)
        )
    else:
        cur = conn.execute(
            "SELECT key, value, category, tags FROM memories WHERE key LIKE ? OR value LIKE ? ORDER BY updated_at DESC LIMIT 20",
            (like, like)
        )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No results found"
    results = []
    for key, value, cat, tags in rows:
        try:
            parsed = json.loads(value)
            preview = json.dumps(parsed, ensure_ascii=False)[:200]
        except (json.JSONDecodeError, TypeError):
            preview = str(value)[:200]
        tags_list = json.loads(tags)
        results.append(f"[{key}] ({cat}) tags: {', '.join(tags_list)}\n  {preview}")
    return "\n\n".join(results)


def forget(key: str) -> str:
    conn = _ensure_db()
    cur = conn.execute("DELETE FROM memories WHERE key = ?", (key,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted:
        return f"Deleted memory '{key}'"
    return f"No memory found for key '{key}'"


def list_by_category(category: str = "") -> str:
    conn = _ensure_db()
    if category:
        cur = conn.execute(
            "SELECT key, category, updated_at FROM memories WHERE category = ? ORDER BY updated_at DESC",
            (category,)
        )
    else:
        cur = conn.execute(
            "SELECT key, category, updated_at FROM memories ORDER BY updated_at DESC"
        )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No memories found"
    lines = ["# Memories", ""]
    for key, cat, updated in rows:
        dt = time.strftime("%Y-%m-%d %H:%M", time.localtime(updated))
        lines.append(f"- [{cat}] {key} (updated: {dt})")
    return "\n".join(lines)


def get_categories() -> list[str]:
    conn = _ensure_db()
    cur = conn.execute("SELECT DISTINCT category FROM memories ORDER BY category")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows


def save_context(session_id: str, content: str) -> str:
    conn = _ensure_db()
    now = time.time()
    conn.execute(
        "INSERT INTO contexts (session_id, content, created_at) VALUES (?, ?, ?)",
        (session_id, content, now)
    )
    conn.commit()
    conn.close()
    return f"Context saved for session '{session_id}'"


def get_context(session_id: str, limit: int = 10) -> str:
    conn = _ensure_db()
    cur = conn.execute(
        "SELECT content, created_at FROM contexts WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
        (session_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return f"No context found for session '{session_id}'"
    lines = [f"# Context: {session_id}", ""]
    for content, created in reversed(rows):
        dt = time.strftime("%Y-%m-%d %H:%M", time.localtime(created))
        lines.append(f"--- {dt} ---")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


def stats() -> str:
    conn = _ensure_db()
    total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    contexts = conn.execute("SELECT COUNT(*) FROM contexts").fetchone()[0]
    cats = conn.execute("SELECT category, COUNT(*) FROM memories GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
    conn.close()
    lines = ["# Knowledge Stats", f"Total memories: {total}", f"Total contexts: {contexts}", ""]
    if cats:
        lines.append("## By category")
        for cat, cnt in cats:
            lines.append(f"  {cat}: {cnt}")
    return "\n".join(lines)
