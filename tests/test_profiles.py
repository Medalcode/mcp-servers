import pytest
from database import init_db
from database.repos import profiles as profile_repo


def test_get_default_profile_no_data():
    init_db()
    profile = profile_repo.get_default_profile()
    assert profile is not None
    assert "personalInfo" in profile
    assert "experience" in profile
    assert "education" in profile
    assert "skills" in profile


def test_create_profile():
    init_db()
    result = profile_repo.create_profile(
        user_id=1,
        name="Test Profile",
        type="professional",
        is_default=True,
        title="Dev",
        summary="Test summary",
        skills=["Python", "Go"],
    )
    assert result["name"] == "Test Profile"
    assert result["isDefault"] is True


def test_list_profiles():
    init_db()
    profiles = profile_repo.list_profiles()
    assert len(profiles) >= 1


def test_delete_profile():
    init_db()
    profile_repo.create_profile(user_id=1, name="Second Profile", type="general")
    profiles = profile_repo.list_profiles()
    assert len(profiles) >= 2
    second_id = profiles[-1]["id"]
    assert profile_repo.delete_profile(second_id) is True


def test_cannot_delete_last_profile():
    init_db()
    profiles = profile_repo.list_profiles()
    assert len(profiles) == 1
    with pytest.raises(ValueError, match="only profile"):
        profile_repo.delete_profile(profiles[0]["id"])
