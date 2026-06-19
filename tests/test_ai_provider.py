import pytest
from unittest.mock import patch, AsyncMock
from services.ai_provider import parse_cv_with_ai, generate_cover_letter, generate_personas

@pytest.fixture(autouse=True)
def reset_engine():
    import services.ai_provider as ap
    ap._engine = None

@pytest.mark.asyncio
@patch("services.ai_provider._get_engine")
async def test_parse_cv_with_ai(mock_get_engine):
    mock_engine = AsyncMock()
    mock_engine.ask = AsyncMock(return_value='```json\n{"personalInfo": {"firstName": "Juan", "lastName": "Perez"}}\n```')
    mock_get_engine.return_value = mock_engine

    result = await parse_cv_with_ai("Test CV text")

    assert mock_engine.ask.called
    assert result == {"personalInfo": {"firstName": "Juan", "lastName": "Perez"}}

@pytest.mark.asyncio
@patch("services.ai_provider._get_engine")
async def test_generate_cover_letter(mock_get_engine):
    mock_engine = AsyncMock()
    mock_engine.ask = AsyncMock(return_value="Estimado equipo, me postulo con gran entusiasmo.")
    mock_get_engine.return_value = mock_engine

    profile = {"personalInfo": {"firstName": "Juan", "lastName": "Perez", "email": "j@j.com"}}
    result = await generate_cover_letter(profile, "Dev", "Acme", "Desc", "professional")

    assert mock_engine.ask.called
    assert "Estimado equipo" in result

@pytest.mark.asyncio
@patch("services.ai_provider._get_engine")
async def test_generate_personas_error(mock_get_engine):
    mock_engine = AsyncMock()
    mock_engine.ask = AsyncMock(side_effect=RuntimeError("API Down"))
    mock_get_engine.return_value = mock_engine

    result = await generate_personas({})

    assert len(result) == 1
    assert "error" in result[0]
