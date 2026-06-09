import sqlite3
import os
import json
import time
from pathlib import Path
from datetime import datetime, date
from typing import Any

def _ensure_db():
    data_dir = Path(os.getenv("MEDALCODE_TASKS_DIR", str(Path.home() / ".medalcode" / "tasks")))
    db_path = data_dir / "tasks.db"
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'pending',
            project TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_deps (
            task_id INTEGER NOT NULL,
            depends_on INTEGER NOT NULL,
            PRIMARY KEY (task_id, depends_on),
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (depends_on) REFERENCES tasks(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn


def create(title: str, priority: str = "medium", project: str = "",
           deadline: str = "", tags: str = "", description: str = "") -> str:
    valid_priorities = ["low", "medium", "high", "critical"]
    if priority not in valid_priorities:
        priority = "medium"
    conn = _ensure_db()
    now = time.time()
    tags_list = json.dumps([t.strip() for t in tags.split(",") if t.strip()])
    cur = conn.execute(
        "INSERT INTO tasks (title, description, priority, project, deadline, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (title, description, priority, project, deadline, tags_list, now, now)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return f"Created task #{task_id}: {title} [{priority}]"


def list_tasks(status: str = "", project: str = "", priority: str = "") -> str:
    conn = _ensure_db()
    query = "SELECT id, title, priority, status, project, deadline, created_at FROM tasks WHERE 1=1"
    params: list[Any] = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if project:
        query += " AND project = ?"
        params.append(project)
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    query += " ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"
    cur = conn.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No tasks found"
    lines = ["# Tasks", ""]
    for tid, title, pri, status, proj, deadline, created in rows:
        pri_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(pri, "⚪")
        deadline_str = f" [due: {deadline}]" if deadline else ""
        proj_str = f" ({proj})" if proj else ""
        lines.append(f"- #{tid} {pri_icon} {title}{proj_str}{deadline_str} [{status}]")
    return "\n".join(lines)


def update(task_id: int, **kwargs) -> str:
    conn = _ensure_db()
    now = time.time()
    allowed = {"title", "description", "priority", "status", "project", "deadline", "tags"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        conn.close()
        return "No valid fields to update"
    updates["updated_at"] = now
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    cur = conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    if cur.rowcount == 0:
        conn.close()
        return f"Task #{task_id} not found"
    conn.commit()
    conn.close()
    updated_fields = ", ".join(updates.keys())
    return f"Updated task #{task_id}: {updated_fields}"


def complete(task_id: int) -> str:
    return update(task_id, status="completed")


def delete(task_id: int) -> str:
    conn = _ensure_db()
    conn.execute("DELETE FROM task_deps WHERE task_id = ? OR depends_on = ?", (task_id, task_id))
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted:
        return f"Deleted task #{task_id}"
    return f"Task #{task_id} not found"


def add_dependency(task_id: int, depends_on: int) -> str:
    conn = _ensure_db()
    # Check both exist
    t1 = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,)).fetchone()
    t2 = conn.execute("SELECT id FROM tasks WHERE id = ?", (depends_on,)).fetchone()
    if not t1:
        conn.close()
        return f"Task #{task_id} not found"
    if not t2:
        conn.close()
        return f"Task #{depends_on} not found"
    try:
        conn.execute("INSERT INTO task_deps (task_id, depends_on) VALUES (?, ?)", (task_id, depends_on))
        conn.commit()
        conn.close()
        return f"Task #{task_id} now depends on task #{depends_on}"
    except sqlite3.IntegrityError:
        conn.close()
        return f"Dependency already exists or would create a cycle"


def remove_dependency(task_id: int, depends_on: int) -> str:
    conn = _ensure_db()
    cur = conn.execute("DELETE FROM task_deps WHERE task_id = ? AND depends_on = ?", (task_id, depends_on))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    if deleted:
        return f"Removed dependency: #{task_id} → #{depends_on}"
    return "Dependency not found"


def get_task(task_id: int) -> str:
    conn = _ensure_db()
    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return f"Task #{task_id} not found"
    columns = [c[1] for c in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    task = dict(zip(columns, row))
    tags_list = json.loads(task["tags"])
    # Get dependencies
    deps = conn.execute(
        "SELECT depends_on, title FROM task_deps JOIN tasks ON task_deps.depends_on = tasks.id WHERE task_id = ?",
        (task_id,)
    ).fetchall()
    dependents = conn.execute(
        "SELECT task_id, title FROM task_deps JOIN tasks ON task_deps.task_id = tasks.id WHERE depends_on = ?",
        (task_id,)
    ).fetchall()
    conn.close()
    lines = [
        f"# #{task['id']} {task['title']}",
        f"Priority: {task['priority']}  |  Status: {task['status']}",
        f"Project: {task['project'] or '(none)'}",
        f"Deadline: {task['deadline'] or '(none)'}",
        f"Tags: {', '.join(tags_list) or '(none)'}",
    ]
    if deps:
        lines.append(f"Depends on: {', '.join(f'#{d[0]} {d[1]}' for d in deps)}")
    if dependents:
        lines.append(f"Blocking: {', '.join(f'#{d[0]} {d[1]}' for d in dependents)}")
    if task["description"]:
        lines.append(f"\n{task['description']}")
    created = time.strftime("%Y-%m-%d %H:%M", time.localtime(task["created_at"]))
    updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(task["updated_at"]))
    lines.append(f"\nCreated: {created}  |  Updated: {updated}")
    return "\n".join(lines)


def stats() -> str:
    conn = _ensure_db()
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    by_status = conn.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
    ).fetchall()
    by_priority = conn.execute(
        "SELECT priority, COUNT(*) FROM tasks GROUP BY priority ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END"
    ).fetchall()
    by_project = conn.execute(
        "SELECT project, COUNT(*) FROM tasks WHERE project != '' GROUP BY project ORDER BY COUNT(*) DESC LIMIT 10"
    ).fetchall()
    overdue = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE deadline != '' AND deadline < date('now') AND status != 'completed'"
    ).fetchone()[0]
    conn.close()
    lines = [
        "# Task Stats",
        f"Total: {total}",
        f"Overdue: {overdue}",
        "",
        "## By Status"
    ]
    for s, c in by_status:
        lines.append(f"  {s}: {c}")
    lines.append("")
    lines.append("## By Priority")
    for p, c in by_priority:
        lines.append(f"  {p}: {c}")
    if by_project:
        lines.append("")
        lines.append("## By Project")
        for p, c in by_project:
            lines.append(f"  {p}: {c}")
    return "\n".join(lines)


def brainstorm(title: str, ideas: str) -> str:
    """Save brainstorming notes as a task with ideas in the description."""
    conn = _ensure_db()
    now = time.time()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, priority, status, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (title, ideas, "medium", "brainstorm", '["brainstorm"]', now, now)
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return f"Saved brainstorm as task #{task_id}: {title}"
