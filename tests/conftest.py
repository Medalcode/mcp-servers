import os
import pytest


def pytest_configure(config):
    """Configure test environment before any collection."""
    os.environ.setdefault("ROUTEMCP_ENABLED", "false")


@pytest.fixture
def sample_profile():
    return {
        "personalInfo": {
            "firstName": "Juan",
            "lastName": "Pérez",
            "email": "juan@example.com",
            "phone": "+56912345678",
            "city": "Santiago",
            "country": "Chile",
            "currentTitle": "Desarrollador Full Stack",
            "summary": "Ingeniero con 5 años de experiencia.",
            "github": "github.com/juanperez",
            "linkedin": "linkedin.com/in/juanperez",
        },
        "experience": [
            {"title": "Dev Full Stack", "company": "TechCorp", "description": "React, Python"},
            {"title": "Junior Dev", "company": "StartupCL", "description": "Mantenimiento sistemas"},
        ],
        "education": [
            {"degree": "Ing. Civil Informática", "school": "U. de Chile", "current": False},
            {"degree": "Diplomado en Data Science", "school": "UAI", "current": True},
        ],
        "skills": ["Python", "JavaScript", "React", "FastAPI", "SQL", "Docker", "Git"],
    }


@pytest.fixture(autouse=True)
def _test_db(tmp_path):
    """Provide a fresh temporary database for each test."""
    db_path = str(tmp_path / "test.db")
    import database
    import database.config
    # Patch DB_PATH in both modules
    database.config.DB_PATH = db_path
    database.DB_PATH = db_path
    # Reset cached connection
    database._db_conn.set(None)
    os.environ["PATHWISE_DB_PATH"] = db_path
    yield
