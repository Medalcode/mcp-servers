import re
from database import get_connection

def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])

def _row_to_camel(row) -> dict:
    return {_to_camel(k): v for k, v in dict(row).items()}

def get_default_profile(user_id=1):
    conn = get_connection()
    cur = conn.execute("SELECT id FROM profiles WHERE user_id=? AND is_default=1 LIMIT 1", (user_id,))
    row = cur.fetchone()
    if not row:
        return None
    return get_full_profile(row["id"])

def get_full_profile(profile_id):
    conn = get_connection()
    profile = {"personalInfo": {}, "experience": [], "education": [], "skills": [], "certifications": [], "languages": []}

    cur = conn.execute("SELECT * FROM personal_info WHERE profile_id=?", (profile_id,))
    row = cur.fetchone()
    if row:
        profile["personalInfo"] = _row_to_camel(row)

    cur = conn.execute("SELECT * FROM experience WHERE profile_id=? ORDER BY order_index", (profile_id,))
    profile["experience"] = [_row_to_camel(r) for r in cur.fetchall()]

    cur = conn.execute("SELECT * FROM education WHERE profile_id=? ORDER BY order_index", (profile_id,))
    profile["education"] = [_row_to_camel(r) for r in cur.fetchall()]

    cur = conn.execute("SELECT name, category FROM skills WHERE profile_id=?", (profile_id,))
    profile["skills"] = [r["name"] for r in cur.fetchall()]

    return profile

def list_profiles(user_id=1):
    conn = get_connection()
    cur = conn.execute(
        "SELECT id, name, type, is_default, created_at FROM profiles WHERE user_id=? ORDER BY is_default DESC, created_at DESC",
        (user_id,))
    return [_row_to_camel(r) for r in cur.fetchall()]

def create_profile(user_id, name, type="general", is_default=False, title="", summary="", skills=None):
    conn = get_connection()
    if is_default:
        conn.execute("UPDATE profiles SET is_default=0 WHERE user_id=?", (user_id,))
    cur = conn.execute("INSERT INTO profiles (user_id, name, type, is_default) VALUES (?,?,?,?)",
                       (user_id, name, type, 1 if is_default else 0))
    profile_id = cur.lastrowid
    if title or summary:
        conn.execute(
            "INSERT INTO personal_info (profile_id, current_title, summary) VALUES (?, ?, ?)",
            (profile_id, title, summary)
        )
    if skills:
        for skill_name in skills:
            conn.execute(
                "INSERT INTO skills (profile_id, name, category) VALUES (?, ?, ?)",
                (profile_id, skill_name, "")
            )
    conn.commit()
    return {"id": profile_id, "name": name, "type": type, "isDefault": is_default}

def delete_profile(profile_id, user_id=1):
    conn = get_connection()
    cur = conn.execute("SELECT COUNT(*) as c FROM profiles WHERE user_id=?", (user_id,))
    if cur.fetchone()["c"] <= 1:
        raise ValueError("Cannot delete the only profile")
    conn.execute("DELETE FROM profiles WHERE id=? AND user_id=?", (profile_id, user_id))
    conn.commit()
    return True
