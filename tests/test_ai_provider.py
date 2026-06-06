import pytest
from unittest.mock import patch, AsyncMock
import json
import os
from services.ai_provider import parse_cv_with_ai, generate_cover_letter, generate_personas

# Habilitar ROUTEMCP para los tests
@pytest.fixture(autouse=True)
def enable_routemcp(monkeypatch):
    monkeypatch.setattr("services.ai_provider.ROUTEMCP_ENABLED", True)

@pytest.mark.asyncio
@patch("services.ai_provider._client.post")
async def test_parse_cv_with_ai(mock_post):
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "content": '```json\n{"personalInfo": {"firstName": "Juan", "lastName": "Perez"}}\n```'
    }
    mock_post.return_value = mock_response

    result = await parse_cv_with_ai("Test CV text")
    
    assert mock_post.called
    assert result == {"personalInfo": {"firstName": "Juan", "lastName": "Perez"}}

@pytest.mark.asyncio
@patch("services.ai_provider._client.post")
async def test_generate_cover_letter(mock_post):
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json.return_value = {
        "content": "Estimado equipo, me postulo con gran entusiasmo."
    }
    mock_post.return_value = mock_response

    profile = {"personalInfo": {"firstName": "Juan"}}
    result = await generate_cover_letter(profile, "Dev", "Acme", "Desc", "professional")
    
    assert mock_post.called
    assert "Estimado equipo" in result

@pytest.mark.asyncio
@patch("services.ai_provider._client.post")
async def test_generate_personas_error(mock_post):
    mock_post.side_effect = Exception("API Down")

    result = await generate_personas({})
    
    assert len(result) == 1
    assert "error" in result[0]
    assert "API Down" in result[0]["error"]
