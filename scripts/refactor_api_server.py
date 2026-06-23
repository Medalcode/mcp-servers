import re

with open("api_server.py", "r") as f:
    content = f.read()

# 1. Add aiosqlite, asynccontextmanager
content = content.replace("import sqlite3", "import sqlite3\nimport aiosqlite\nfrom contextlib import asynccontextmanager")

# 2. Add lifespan
lifespan_code = """
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("PRAGMA journal_mode=WAL;")
        await conn.execute('''CREATE TABLE IF NOT EXISTS metrics (
                            key TEXT PRIMARY KEY,
                            value INTEGER
                        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )''')
        await conn.execute('''CREATE TABLE IF NOT EXISTS task_results (
                            task_id TEXT PRIMARY KEY,
                            status TEXT,
                            data TEXT
                        )''')
        defaults = {"jobs_scanned": 0, "successful_logins": 0, "accounts_created": 0, "applications_sent": 0}
        for k, v in defaults.items():
            await conn.execute("INSERT OR IGNORE INTO metrics (key, value) VALUES (?, ?)", (k, v))
        await conn.commit()
    yield

"""
content = content.replace('app = FastAPI(title="Pathwise UI Dashboard")', lifespan_code + 'app = FastAPI(title="Pathwise UI Dashboard", lifespan=lifespan)')

# 3. Replace old DB logic
old_db_logic = """def _get_db():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with _get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS metrics (
                            key TEXT PRIMARY KEY,
                            value INTEGER
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            message TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS task_results (
                            task_id TEXT PRIMARY KEY,
                            status TEXT,
                            data TEXT
                        )''')
        defaults = {"jobs_scanned": 0, "successful_logins": 0, "accounts_created": 0, "applications_sent": 0}
        for k, v in defaults.items():
            conn.execute("INSERT OR IGNORE INTO metrics (key, value) VALUES (?, ?)", (k, v))
init_db()

def update_metric(key: str, amount: int = 1):
    with _get_db() as conn:
        conn.execute("UPDATE metrics SET value = value + ? WHERE key = ?", (amount, key))

def get_metrics_dict():
    with _get_db() as conn:
        metrics = {row[0]: row[1] for row in conn.execute("SELECT key, value FROM metrics")}
        logs = [row[0] for row in conn.execute("SELECT message FROM logs ORDER BY id DESC LIMIT 50")]
        metrics["recent_logs"] = logs[::-1]
        return metrics

def add_log(msg: str):
    with _get_db() as conn:
        conn.execute("INSERT INTO logs (message) VALUES (?)", (msg,))
    manager.broadcast(msg)"""

new_db_logic = """async def update_metric(key: str, amount: int = 1):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("UPDATE metrics SET value = value + ? WHERE key = ?", (amount, key))
        await conn.commit()

async def get_metrics_dict():
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        async with conn.execute("SELECT key, value FROM metrics") as cursor:
            metrics = {row[0]: row[1] async for row in cursor}
        async with conn.execute("SELECT message FROM logs ORDER BY id DESC LIMIT 50") as cursor:
            logs = [row[0] async for row in cursor]
        metrics["recent_logs"] = logs[::-1]
        return metrics

async def add_log(msg: str):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO logs (message) VALUES (?)", (msg,))
        await conn.commit()
    manager.broadcast(msg)"""

content = content.replace(old_db_logic, new_db_logic)

# 4. Await add_log and update_metric
content = re.sub(r'(?<!await )add_log\(', 'await add_log(', content)
content = re.sub(r'(?<!await )update_metric\(', 'await update_metric(', content)
content = re.sub(r'(?<!await )get_metrics_dict\(', 'await get_metrics_dict(', content)

# 5. Fix `with _get_db() as conn:` in `get_task_status` and `bg_search` etc
content = re.sub(
    r'with _get_db\(\) as conn:\n\s+row = conn\.execute\("SELECT status, data FROM task_results WHERE task_id = \?", \(task_id,\)\)\.fetchone\(\)',
    r'async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:\n        async with conn.execute("SELECT status, data FROM task_results WHERE task_id = ?", (task_id,)) as cursor:\n            row = await cursor.fetchone()',
    content
)

content = re.sub(
    r'with _get_db\(\) as conn:\n\s+conn\.execute\("INSERT INTO task_results \(task_id, status, data\) VALUES \(\?, \?, \?\)",\n\s+\(task_id, "completed", json\.dumps\(data\)\)\)',
    r'async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:\n        await conn.execute("INSERT INTO task_results (task_id, status, data) VALUES (?, ?, ?) ON CONFLICT(task_id) DO UPDATE SET status=excluded.status, data=excluded.data", (task_id, "completed", json.dumps(data)))\n        await conn.commit()',
    content
)
content = re.sub(
    r'with _get_db\(\) as conn:\n\s+conn\.execute\("INSERT INTO task_results \(task_id, status, data\) VALUES \(\?, \?, \?\)",\n\s+\(task_id, "error", str\(e\)\)\)',
    r'async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:\n        await conn.execute("INSERT INTO task_results (task_id, status, data) VALUES (?, ?, ?) ON CONFLICT(task_id) DO UPDATE SET status=excluded.status, data=excluded.data", (task_id, "error", str(e)))\n        await conn.commit()',
    content
)

with open("api_server.py", "w") as f:
    f.write(content)

print("Refactored api_server.py successfully.")
