from database import init_db
from database.repos import applications as app_repo


def test_create_application():
    init_db()
    app_id = app_repo.create_application(
        user_id=1,
        job_title="Full Stack Dev",
        company="TechCorp",
        url="https://example.com/apply",
        status="to_apply",
    )
    assert app_id is not None


def test_list_applications():
    init_db()
    app_repo.create_application(1, "Dev", "Company A")
    app_repo.create_application(1, "Engineer", "Company B")
    apps = app_repo.list_applications()
    assert len(apps) == 2


def test_get_application():
    init_db()
    app_id = app_repo.create_application(1, "Dev", "Company A")
    app = app_repo.get_application(app_id)
    assert app is not None
    assert app["job_title"] == "Dev"
    assert app["company"] == "Company A"


def test_update_application():
    init_db()
    app_id = app_repo.create_application(1, "Dev", "Company A")
    app_repo.update_application(app_id, 1, status="applied")
    app = app_repo.get_application(app_id)
    assert app["status"] == "applied"


def test_patch_status():
    init_db()
    app_id = app_repo.create_application(1, "Dev", "Company A")
    assert app_repo.patch_status(app_id, 1, "interview") is True
    app = app_repo.get_application(app_id)
    assert app["status"] == "interview"


def test_delete_application():
    init_db()
    app_id = app_repo.create_application(1, "Dev", "Company A")
    assert app_repo.delete_application(app_id) is True
    assert app_repo.get_application(app_id) is None


def test_get_stats():
    init_db()
    app_repo.create_application(1, "Dev", "A", status="applied")
    app_repo.create_application(1, "Eng", "B", status="interview")
    app_repo.create_application(1, "PM", "C", status="applied")
    stats = app_repo.get_stats()
    assert stats["total"] == 3
    assert stats["by_status"]["applied"] == 2
    assert stats["by_status"]["interview"] == 1
    assert stats["response_rate"] > 0
