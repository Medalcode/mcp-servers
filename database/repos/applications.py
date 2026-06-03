from database import get_connection

def list_applications(user_id=1, status=None, limit=100, offset=0):
    conn = get_connection()
    query = "SELECT * FROM applications WHERE user_id=?"
    params = [user_id]
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cur = conn.execute(query, params)
    return [dict(r) for r in cur.fetchall()]

def get_application(app_id, user_id=1):
    conn = get_connection()
    cur = conn.execute("SELECT * FROM applications WHERE id=? AND user_id=?", (app_id, user_id))
    row = cur.fetchone()
    return dict(row) if row else None

def create_application(user_id, job_title, company, url=None, status="to_apply",
                       profile_id=None, salary_range=None, location=None, notes=None):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO applications (user_id, profile_id, job_title, company, url, status, salary_range, location, notes)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, profile_id, job_title, company, url, status, salary_range, location, notes))
    conn.commit()
    return cur.lastrowid

_COLUMN_MAP = {
    "job_title": "job_title", "company": "company", "url": "url",
    "status": "status", "salary_range": "salary_range",
    "location": "location", "notes": "notes",
}

def update_application(app_id, user_id, **kwargs):
    conn = get_connection()
    sets = {}
    for k, v in kwargs.items():
        col = _COLUMN_MAP.get(k)
        if col and v is not None:
            sets[col] = v
    if not sets:
        return False
    cols = list(sets.keys())
    placeholders = ", ".join(f"{c}=?" for c in cols)
    params = [sets[c] for c in cols] + [app_id, user_id]
    query = f"UPDATE applications SET {placeholders} WHERE id=? AND user_id=?"
    conn.execute(query, params)
    conn.commit()
    return True

def patch_status(app_id, user_id, status):
    conn = get_connection()
    cur = conn.execute("UPDATE applications SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?",
                       (status, app_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def delete_application(app_id, user_id=1):
    conn = get_connection()
    cur = conn.execute("DELETE FROM applications WHERE id=? AND user_id=?", (app_id, user_id))
    conn.commit()
    return cur.rowcount > 0

def get_stats(user_id=1):
    conn = get_connection()
    cur = conn.execute("SELECT status, COUNT(*) as count FROM applications WHERE user_id=? GROUP BY status", (user_id,))
    stats = {r["status"]: r["count"] for r in cur.fetchall()}

    cur = conn.execute("SELECT COUNT(*) as c FROM applications WHERE user_id=? AND created_at >= datetime('now', '-7 days')", (user_id,))
    week_count = cur.fetchone()["c"]

    total = sum(stats.values())
    applied = stats.get("applied", 0)
    interview = stats.get("interview", 0)
    offer = stats.get("offer", 0)
    response_rate = round((interview + offer) / applied * 100, 1) if applied > 0 else 0

    return {"total": total, "by_status": stats, "response_rate": response_rate, "this_week": week_count}
