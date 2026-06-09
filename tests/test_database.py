import sqlite3
import pytest

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
    assert "applications" in names

def test_init_db_creates_default_admin(db_connection):
    cur = db_connection.execute("SELECT email, password_hash FROM users")
    row = cur.fetchone()
    assert row is not None
    assert row["email"] == "admin@pathwise.local"

def test_init_db_seeds_default_profile(db_connection):
    cur = db_connection.execute("SELECT name, type FROM profiles")
    row = cur.fetchone()
    assert row is not None
    assert row["name"] == "Default Profile"

def test_fts5_virtual_tables(db_connection):
    db_connection.execute("""
        INSERT INTO companies (name, description) VALUES ('TestCo', 'A very specific keyword company')
    """)
    db_connection.commit()
    
    cur = db_connection.execute("""
        SELECT * FROM companies_fts WHERE companies_fts MATCH 'keyword'
    """)
    rows = cur.fetchall()
    assert len(rows) > 0
    assert rows[0]["name"] == "TestCo"

def test_applications_crud(db_connection):
    db_connection.execute("""
        INSERT INTO applications (job_title, company) VALUES ('Engineer', 'Acme')
    """)
    db_connection.commit()
    
    cur = db_connection.execute("SELECT status FROM applications WHERE company = 'Acme'")
    row = cur.fetchone()
    assert row["status"] == "to_apply"
    
    with pytest.raises(sqlite3.IntegrityError):
        db_connection.execute("""
            INSERT INTO applications (job_title, company, status) VALUES ('Eng', 'Bcorp', 'invalid_status')
        """)
