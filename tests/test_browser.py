import pytest
from servers.browser import (
    _validate_url, _validate_script, _dns_resolves,
    _is_private_hostname,
)


class TestValidateURL:
    def test_http_allowed(self):
        _validate_url("http://example.com")

    def test_https_allowed(self):
        _validate_url("https://example.com")

    def test_ftp_rejected(self):
        with pytest.raises(ValueError, match="Scheme"):
            _validate_url("ftp://example.com")

    def test_file_scheme_rejected(self):
        with pytest.raises(ValueError, match="Scheme"):
            _validate_url("file:///etc/passwd")

    def test_localhost_rejected(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            _validate_url("http://localhost:8080")

    def test_localhost_ip_rejected(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            _validate_url("http://127.0.0.1:8080")

    def test_private_ip_rejected(self):
        with pytest.raises(ValueError, match="Blocked private IP"):
            _validate_url("http://192.168.1.1")

    def test_link_local_rejected(self):
        with pytest.raises(ValueError, match="Blocked hostname|Blocked private"):
            _validate_url("http://169.254.169.254")

    def test_internal_domain_rejected(self):
        with pytest.raises(ValueError, match="Blocked domain"):
            _validate_url("http://internal.service.local")

    def test_metadata_google_rejected(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            _validate_url("http://metadata.google.internal")

    def test_credentials_rejected(self):
        with pytest.raises(ValueError, match="URL credentials"):
            _validate_url("http://user:pass@example.com")

    def test_unresolvable_hostname_rejected(self):
        with pytest.raises(ValueError, match="does not resolve"):
            _validate_url("http://this-domain-does-not-exist-12345.com")

    def test_valid_url_with_query_params(self):
        _validate_url("https://www.google.com/search?q=test")

    def test_valid_http(self):
        _validate_url("http://example.com")


class TestDNSResolves:
    def test_known_host_resolves(self):
        assert _dns_resolves("example.com") is True

    def test_empty_hostname(self):
        assert _dns_resolves("") is False

    def test_nonexistent_host(self):
        assert _dns_resolves("this-domain-does-not-exist-99999.com") is False


class TestIsPrivateHostname:
    def test_localhost_ipv4(self):
        assert _is_private_hostname("127.0.0.1") is True

    def test_public_hostname(self):
        assert _is_private_hostname("example.com") is False

    def test_private_ip(self):
        assert _is_private_hostname("10.0.0.1") is True

    def test_link_local(self):
        assert _is_private_hostname("169.254.1.1") is True

    def test_empty(self):
        assert _is_private_hostname("") is False


class TestValidateScript:
    def test_simple_dom_access_allowed(self):
        _validate_script("return document.title")

    def test_eval_blocked(self):
        with pytest.raises(ValueError, match="eval"):
            _validate_script("evAl(code)")

    def test_fetch_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("fetch('/api')")

    def test_websocket_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("new WebSocket('ws://evil')")

    def test_function_constructor_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("new Function('return 1')")

    def test_import_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("import('http://evil')")

    def test_document_write_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("document.write('evil')")

    def test_set_timeout_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("sEtTimeout(evil, 100)")

    def test_alert_blocked(self):
        with pytest.raises(ValueError, match="dangerous"):
            _validate_script("alert('xss')")
