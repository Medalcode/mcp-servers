import hashlib
import os
import sqlite3

from database import init_db, get_connection


def test_init_db_creates_tables():
    init_db()
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r["name"] for r in tables]
    assert "users" in names
    assert "profiles" in names
    assert "personal_info" in names
    assert "experience" in names
    assert "education" in names
    assert "skills" in names
    assert "applications" in names
    assert "companies" in names
    assert "company_reviews" in names
    assert "interview_questions" in names
    assert "search_history" in names


def test_init_db_creates_default_admin():
    init_db()
    conn = get_connection()
    cur = conn.execute("SELECT email, password_hash FROM users")
    row = cur.fetchone()
    assert row is not None
    assert row["email"] == "admin@pathwise.local"


def test_init_db_uses_env_password():
    os.environ["PATHWISE_ADMIN_PASSWORD"] = "test-secret-123"
    init_db()
    conn = get_connection()
    cur = conn.execute("SELECT password_hash FROM users")
    row = cur.fetchone()
    assert ":" in row["password_hash"]
    salt, hash_val = row["password_hash"].split(":", 1)
    expected = hashlib.sha256((salt + "test-secret-123").encode()).hexdigest()
    assert hash_val == expected


def test_init_db_seeds_default_profile():
    init_db()
    conn = get_connection()
    cur = conn.execute("SELECT name, type FROM profiles")
    row = cur.fetchone()
    assert row is not None
    assert row["name"] == "Default Profile"


def test_init_db_idempotent():
    init_db()
    conn = get_connection()
    count1 = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    init_db()
    count2 = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    assert count1 == count2 == 1


def test_fts_tables():
    init_db()
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%fts%'"
    ).fetchall()
    names = [r["name"] for r in tables]
    assert "applications_fts" in names
    assert "companies_fts" in names
