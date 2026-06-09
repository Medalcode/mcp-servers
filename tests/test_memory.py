import pytest
from memory_engine.store import remember, recall, search, forget, list_by_category, stats, get_categories


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setenv("MEDALCODE_MEMORY_DIR", str(tmp_path))
    yield


def test_remember_and_recall():
    result = remember("test-key", "hello world", "testing")
    assert "Stored" in result
    result = recall("test-key")
    assert "hello world" in result


def test_remember_json_value():
    remember("json-key", {"name": "test", "count": 42}, "testing")
    result = recall("json-key")
    assert "test" in result


def test_forget():
    remember("forget-me", "data", "testing")
    result = forget("forget-me")
    assert "Deleted" in result
    result = recall("forget-me")
    assert "No memory found" in result


def test_search():
    remember("search-foo", "bar baz", "testing")
    remember("search-bar", "foo baz", "other")
    results = search("foo")
    assert len(results) > 0


def test_search_by_category():
    remember("cat-test", "hello world", "special")
    results = search("hello", category="special")
    assert "cat-test" in results


def test_list_categories():
    remember("k1", "v1", "cat-a")
    remember("k2", "v2", "cat-b")
    cats = get_categories()
    assert "cat-a" in cats
    assert "cat-b" in cats


def test_list_by_category():
    remember("k1", "v1", "group")
    remember("k2", "v2", "group")
    result = list_by_category("group")
    assert "k1" in result
    assert "k2" in result


def test_stats():
    remember("a", "1", "x")
    remember("b", "2", "y")
    result = stats()
    assert "2" in result
