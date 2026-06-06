from scrapers.exporters import to_csv, to_markdown, _sanitize


def test_sanitize_formula_chars():
    assert _sanitize("=SUM(A1:A10)") == "'=SUM(A1:A10)"
    assert _sanitize("+cmd") == "'+cmd"
    assert _sanitize("-cmd") == "'-cmd"
    assert _sanitize("@cmd") == "'@cmd"
    assert _sanitize("normal text") == "normal text"
    assert _sanitize("") == ""


def test_csv_simple():
    data = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
    result = to_csv(data)
    assert "name,age" in result
    assert "Alice,30" in result
    assert "Bob,25" in result


def test_csv_with_formula_injection():
    data = [{"name": "=SUM(A1:A10)", "value": "100"}]
    result = to_csv(data)
    assert "'=SUM(A1:A10)" in result
    assert ",100" in result


def test_csv_items_dict():
    data = {"items": [{"x": "1"}, {"x": "2"}]}
    result = to_csv(data)
    assert "x" in result
    assert "1" in result


def test_csv_empty_data():
    assert to_csv([]) == "[]"


def test_markdown_simple():
    data = [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
    result = to_markdown(data)
    assert "| name | age |" in result
    assert "| --- | --- |" in result
    assert "| Alice | 30 |" in result


def test_markdown_dict():
    data = {"title": "Test", "count": 5}
    result = to_markdown(data)
    assert "**title**" in result
    assert "**count**" in result


def test_markdown_dict_with_list():
    data = {"items": [{"id": "1"}, {"id": "2"}]}
    result = to_markdown(data)
    assert "## items" in result
    assert "| id |" in result
