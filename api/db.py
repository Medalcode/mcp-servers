import aiosqlite

DB_PATH = "metrics.db"

async def update_metric(key: str, amount: int = 1):
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

async def add_log(msg: str, broadcast_func=None):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO logs (message) VALUES (?)", (msg,))
        await conn.commit()
    if broadcast_func:
        broadcast_func(msg)

async def create_task(task_id: str):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))
        await conn.commit()

async def update_task_status(task_id: str, status: str, data: str):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        await conn.execute("UPDATE task_results SET status = ?, data = ? WHERE task_id = ?", (status, data, task_id))
        await conn.commit()

async def get_task(task_id: str):
    async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:
        async with conn.execute("SELECT status, data FROM task_results WHERE task_id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
        return row
