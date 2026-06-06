import pytest
from database import init_db, get_connection
from database.repos import applications as app_repo
from database.repos import profiles as profile_repo


def test_applications_crud():
    init_db()
    app_id = app_repo.create_application(1, "Full Stack Dev", "TechCorp", "https://example.com/job")
    assert app_id is not None
    assert app_id > 0

    app = app_repo.get_application(app_id)
    assert app is not None
    assert app["job_title"] == "Full Stack Dev"
    assert app["company"] == "TechCorp"

    apps = app_repo.list_applications()
    assert len(apps) == 1

    app_repo.patch_status(app_id, 1, "applied")
    app = app_repo.get_application(app_id)
    assert app["status"] == "applied"

    deleted = app_repo.delete_application(app_id)
    assert deleted is True

    app = app_repo.get_application(app_id)
    assert app is None


def test_applications_with_location():
    init_db()
    id1 = app_repo.create_application(1, "Dev", "CoA", location="Santiago")
    id2 = app_repo.create_application(1, "Dev", "CoA", location="Remote")

    apps = app_repo.list_applications()
    assert len(apps) >= 2

    app_repo.delete_application(id1)
    app_repo.delete_application(id2)


def test_applications_stats():
    init_db()
    app_repo.create_application(1, "Dev", "Co1", status="applied")
    app_repo.create_application(1, "Dev", "Co2", status="applied")
    app_repo.create_application(1, "Dev", "Co3", status="interview")

    stats = app_repo.get_stats()
    assert stats["total"] >= 3
    assert stats["by_status"].get("applied", 0) >= 2
    assert stats["by_status"].get("interview", 0) >= 1
    assert stats["response_rate"] >= 0


def test_profiles_crud():
    init_db()
    result = profile_repo.create_profile(1, "Test Profile")
    assert result is not None
    assert result["id"] > 0

    profiles = profile_repo.list_profiles(1)
    names = [p["name"] for p in profiles]
    assert "Test Profile" in names

    deleted = profile_repo.delete_profile(result["id"], 1)
    assert deleted is True

    profiles = profile_repo.list_profiles(1)
    names = [p["name"] for p in profiles]
    assert "Test Profile" not in names


def test_profile_default():
    init_db()
    profile = profile_repo.get_default_profile(1)
    assert profile is not None
    assert isinstance(profile, dict)
    assert "skills" in profile
    assert "experience" in profile
    assert "education" in profile
    assert "personalInfo" in profile


def test_cannot_delete_last_profile():
    init_db()
    profiles = profile_repo.list_profiles(1)
    count_before = profiles
    with pytest.raises(ValueError, match="Cannot delete the only profile"):
        profile_repo.delete_profile(profiles[0]["id"], 1)
