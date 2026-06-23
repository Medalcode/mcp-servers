import re

with open("api_server.py", "r") as f:
    content = f.read()

# Replace with _get_db() as conn:\n        conn.execute(...)
# We can use regex to find them all
content = re.sub(
    r'(\s+)with _get_db\(\) as conn:\n(\s+)conn\.execute\((.*?)\)',
    r'\1async with aiosqlite.connect(DB_PATH, timeout=20.0) as conn:\n\2await conn.execute(\3)\n\2await conn.commit()',
    content
)

with open("api_server.py", "w") as f:
    f.write(content)
print("Fixed remaining _get_db usages")
