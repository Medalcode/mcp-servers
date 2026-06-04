import logging
import os
import sqlite3
from contextvars import ContextVar
from pathlib import Path

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

from database.config import DB_PATH

logger = logging.getLogger(__name__)

_db_conn: ContextVar[sqlite3.Connection | None] = ContextVar('db_connection', default=None)


def get_connection() -> sqlite3.Connection:
    conn = _db_conn.get()
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _db_conn.set(conn)
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            name TEXT NOT NULL,
            type TEXT,
            is_default BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS personal_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            first_name TEXT, last_name TEXT, email TEXT, phone TEXT,
            address TEXT, city TEXT, country TEXT, postal_code TEXT,
            current_title TEXT, linkedin TEXT, portfolio TEXT, github TEXT,
            summary TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            title TEXT NOT NULL, company TEXT NOT NULL, location TEXT,
            start_date TEXT, end_date TEXT, current BOOLEAN DEFAULT 0,
            description TEXT, order_index INTEGER DEFAULT 0,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            degree TEXT NOT NULL, school TEXT NOT NULL, field_of_study TEXT,
            start_date TEXT, end_date TEXT, current BOOLEAN DEFAULT 0,
            description TEXT, order_index INTEGER DEFAULT 0,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            name TEXT NOT NULL, category TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL DEFAULT 1,
            profile_id INTEGER,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            status TEXT DEFAULT 'to_apply'
                CHECK(status IN ('to_apply','applied','interview','offer','rejected')),
            url TEXT,
            salary_range TEXT,
            location TEXT,
            applied_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            website TEXT,
            industry TEXT,
            size TEXT,
            description TEXT,
            culture TEXT,
            tech_stack TEXT,
            glassdoor_rating REAL CHECK(glassdoor_rating BETWEEN 0 AND 5),
            linkedin_url TEXT,
            careers_url TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS company_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            source TEXT,
            rating REAL,
            pros TEXT,
            cons TEXT,
            reviewed_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS interview_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            company TEXT NOT NULL,
            job_title TEXT NOT NULL,
            question_type TEXT DEFAULT 'technical',
            question TEXT NOT NULL,
            answer TEXT,
            difficulty TEXT DEFAULT 'medium',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            location TEXT,
            remote_only BOOLEAN DEFAULT 0,
            result_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
        CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
        CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created_at);
        CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
        CREATE INDEX IF NOT EXISTS idx_interview_questions_company ON interview_questions(company);
        CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id);
        CREATE INDEX IF NOT EXISTS idx_interview_questions_app ON interview_questions(application_id);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_profile_name ON skills(profile_id, name);
    """)
    conn.commit()

    # Enable FTS5 for full-text search on applications and companies
    try:
        conn.executescript("""
            CREATE VIRTUAL TABLE IF NOT EXISTS applications_fts USING fts5(
                job_title, company, notes,
                content='applications',
                content_rowid='id'
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS companies_fts USING fts5(
                name, description, culture, tech_stack, notes,
                content='companies',
                content_rowid='id'
            );
            CREATE TRIGGER IF NOT EXISTS applications_ai AFTER INSERT ON applications BEGIN
                INSERT INTO applications_fts(rowid, job_title, company, notes) VALUES (new.id, new.job_title, new.company, new.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS applications_ad AFTER DELETE ON applications BEGIN
                INSERT INTO applications_fts(applications_fts, rowid, job_title, company, notes) VALUES('delete', old.id, old.job_title, old.company, old.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS applications_au AFTER UPDATE ON applications BEGIN
                INSERT INTO applications_fts(applications_fts, rowid, job_title, company, notes) VALUES('delete', old.id, old.job_title, old.company, old.notes);
                INSERT INTO applications_fts(rowid, job_title, company, notes) VALUES (new.id, new.job_title, new.company, new.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS companies_ai AFTER INSERT ON companies BEGIN
                INSERT INTO companies_fts(rowid, name, description, culture, tech_stack, notes) VALUES (new.id, new.name, new.description, new.culture, new.tech_stack, new.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS companies_ad AFTER DELETE ON companies BEGIN
                INSERT INTO companies_fts(companies_fts, rowid, name, description, culture, tech_stack, notes) VALUES('delete', old.id, old.name, old.description, old.culture, old.tech_stack, old.notes);
            END;
            CREATE TRIGGER IF NOT EXISTS companies_au AFTER UPDATE ON companies BEGIN
                INSERT INTO companies_fts(companies_fts, rowid, name, description, culture, tech_stack, notes) VALUES('delete', old.id, old.name, old.description, old.culture, old.tech_stack, old.notes);
                INSERT INTO companies_fts(rowid, name, description, culture, tech_stack, notes) VALUES (new.id, new.name, new.description, new.culture, new.tech_stack, new.notes);
            END;
        """)
        conn.commit()
    except Exception as e:
        logger.warning("FTS5 not available: %s", e)

    # Ensure hash indexes exist on tables used for lookups
    conn.execute("PRAGMA optimize")

    cur = conn.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        admin_pass = os.environ.get("PATHWISE_ADMIN_PASSWORD")
        if not admin_pass:
            raise RuntimeError(
                "PATHWISE_ADMIN_PASSWORD environment variable must be set on first run"
            )
        if HAS_BCRYPT:
            pw_hash = bcrypt.hashpw(admin_pass.encode(), bcrypt.gensalt()).decode()
        else:
            pw_hash = admin_pass
            logger.warning("bcrypt not available, storing admin password insecurely")
        conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)",
                     ("admin@pathwise.local", pw_hash))
        conn.commit()

    cur = conn.execute("SELECT COUNT(*) FROM profiles")
    if cur.fetchone()[0] == 0:
        _seed_default_profile(conn)


def _seed_default_profile(conn):
    conn.execute("INSERT OR IGNORE INTO profiles (name, type) VALUES (?, ?)", ("Default Profile", "professional"))
    profile_id = conn.execute("SELECT id FROM profiles LIMIT 1").fetchone()[0]
    conn.execute("INSERT OR IGNORE INTO personal_info (profile_id, first_name, email, phone, city, country) VALUES (?, ?, ?, ?, ?, ?)",
                 (profile_id, "", "", "", "", ""))
    conn.commit()
