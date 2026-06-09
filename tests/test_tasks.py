import pytest
from task_tracker.engine import create, list_tasks, complete, delete, get_task, stats, add_dependency, remove_dependency


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDALCODE_TASKS_DIR", str(tmp_path))
    yield


def test_create_task():
    result = create("Test task", "high", "test-project", "2026-12-31", "urgent,feature")
    assert "Created task #1" in result


def test_list_tasks():
    create("A task", "medium")
    result = list_tasks()
    assert "A task" in result


def test_list_by_status():
    create("Pending task", "medium")
    result = list_tasks(status="pending")
    assert "Pending task" in result
    complete(1)
    result = list_tasks(status="pending")
    assert result == "No tasks found"


def test_complete_task():
    create("To complete", "low")
    result = complete(1)
    assert "Updated" in result
    t = get_task(1)
    assert "completed" in t


def test_delete_task():
    create("delete-me", "low")
    result = delete(1)
    assert "Deleted" in result
    result = delete(1)
    assert "not found" in result


def test_get_task():
    create("My Task", "high", "my-project")
    result = get_task(1)
    assert "My Task" in result
    assert "my-project" in result


def test_stats():
    create("Task A", "high")
    create("Task B", "low")
    result = stats()
    assert "Total" in result
    assert "2" in result


def test_dependencies():
    create("parent", "medium")
    create("child", "high")
    result = add_dependency(2, 1)
    assert "depends" in result
    result = get_task(2)
    assert "parent" in result or "depends on" in result
    result = remove_dependency(2, 1)
    assert "Removed" in result
    result = remove_dependency(2, 1)
    assert "not found" in result
