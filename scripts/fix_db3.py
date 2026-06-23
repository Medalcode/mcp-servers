import re

with open("api_server.py", "r") as f:
    content = f.read()

# Fix 1: INSERT INTO task_results (task_id, status)\n        await conn.commit() VALUES (?, 'running')", (task_id,))
content = content.replace(
    '''await conn.execute("INSERT INTO task_results (task_id, status)\n        await conn.commit() VALUES (?, 'running')", (task_id,))''',
    '''await conn.execute("INSERT INTO task_results (task_id, status) VALUES (?, 'running')", (task_id,))\n        await conn.commit()'''
)

# Fix 2: UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?\n            await conn.commit(), task_id))
content = content.replace(
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?\n            await conn.commit(), task_id))''',
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(jobs), task_id))\n            await conn.commit()'''
)

# Fix 3: UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?\n            await conn.commit()}), task_id))
content = content.replace(
    '''await conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?\n            await conn.commit()}), task_id))''',
    '''await conn.execute("UPDATE task_results SET status = 'error', data = ? WHERE task_id = ?", (json.dumps({"message": str(e)}), task_id))\n            await conn.commit()'''
)

# Fix 4: For register endpoint success
content = content.replace(
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?\n            await conn.commit(), task_id))''',
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps(results), task_id))\n            await conn.commit()'''
)

# Fix 5: For batch apply success
content = content.replace(
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?\n        await conn.commit()}), task_id))''',
    '''await conn.execute("UPDATE task_results SET status = 'success', data = ? WHERE task_id = ?", (json.dumps({"success": success_count, "total": len(urls)}), task_id))\n        await conn.commit()'''
)

with open("api_server.py", "w") as f:
    f.write(content)
print("api_server.py repaired")
