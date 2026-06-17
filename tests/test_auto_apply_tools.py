import pytest
from tools.auto_apply_tools import _css_escape, _safe_selector


class TestCssEscape:
    def test_simple_value(self):
        assert _css_escape("email") == '"email"'

    def test_contains_backslash(self):
        assert _css_escape("test\\name") == '"test\\\\name"'

    def test_contains_double_quote(self):
        assert _css_escape('test"name') == '"test\\"name"'

    def test_contains_both(self):
        assert _css_escape('test\\"name') == '"test\\\\\\"name"'

    def test_empty(self):
        assert _css_escape("") == '""'

    def test_special_chars(self):
        result = _css_escape("user[name]")
        assert result == '"user[name]"'


class TestSafeSelector:
    def test_simple_tag_name(self):
        assert _safe_selector("input", "email") == 'input[name="email"]'

    def test_with_value(self):
        assert _safe_selector("input", "checkbox", "yes") == 'input[name="checkbox"][value="yes"]'

    def test_name_with_backslash(self):
        assert _safe_selector("input", "test\\name") == 'input[name="test\\\\name"]'

    def test_name_with_quote(self):
        sel = _safe_selector("textarea", 'field"name')
        assert sel == 'textarea[name="field\\"name"]'

    def test_value_with_special_chars(self):
        sel = _safe_selector("select", "city", "Santiago, Chile")
        assert sel == 'select[name="city"][value="Santiago, Chile"]'
