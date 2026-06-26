import pytest

from scrapers.base import _validate_url


class TestValidateUrl:
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
        with pytest.raises(ValueError, match="Blocked IP"):
            _validate_url("http://192.168.1.1")

    def test_internal_domain_rejected(self):
        with pytest.raises(ValueError, match="Blocked domain"):
            _validate_url("http://internal.service.local")

    def test_metadata_google_rejected(self):
        with pytest.raises(ValueError, match="Blocked hostname"):
            _validate_url("http://169.254.169.254")

    def test_unresolvable_hostname_rejected(self):
        with pytest.raises(ValueError, match="Cannot resolve"):
            _validate_url("http://this-domain-does-not-exist-12345.com")

    def test_valid_public_url(self):
        _validate_url("https://www.google.com/search?q=test")
        _validate_url("http://example.com")

import os
from unittest.mock import patch, AsyncMock
from services.scrapers.computrabajo import scan_computrabajo

@pytest.mark.asyncio
async def test_computrabajo_contract_parsing():
    # Load HTML fixture
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'computrabajo_mock.html')
    with open(fixture_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # Mock httpx AsyncClient
    mock_response = AsyncMock()
    mock_response.text = html_content
    mock_response.raise_for_status.return_value = None
    
    with patch('httpx.AsyncClient.get', return_value=mock_response):
        jobs = await scan_computrabajo("python", "santiago")
        
    assert len(jobs) == 1
    job = jobs[0]
    assert job["title"] == "Software Engineer"
    assert job["company"] == "TechCorp"
    assert job["location"] == "Santiago Metropolitana"
    assert job["url"] == "https://cl.computrabajo.com/oferta-de-trabajo-123"
