import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from servers.route import route, ask, compare, models, classify_task
from router.models import ModelInfo

@pytest.fixture
def mock_engine():
    with patch("servers.route.engine") as mock:
        yield mock

@pytest.mark.asyncio
async def test_route_tool(mock_engine):
    mock_engine.route = AsyncMock(return_value="Routed Response")
    result = await route("Hola, necesito ayuda", "general")
    assert result == "Routed Response"
    mock_engine.route.assert_called_once_with("Hola, necesito ayuda", "general")

@pytest.mark.asyncio
async def test_ask_tool_success(mock_engine):
    # Mocking available models
    with patch("servers.route.MODELS", [ModelInfo(id="gemini-test", provider="google", name="Gemini", strengths=[], context_window=1000, speed="fast", cost="low")]):
        mock_prov = AsyncMock()
        mock_prov.is_available.return_value = True
        mock_engine.providers = {"google": mock_prov}
        
        mock_engine.ask = AsyncMock(return_value="Answer from Gemini")
        result = await ask("gemini-test", "Pregunta")
        assert result == "Answer from Gemini"
        mock_engine.ask.assert_called_once_with("gemini-test", "Pregunta", temperature=0.7, max_tokens=8192)

@pytest.mark.asyncio
async def test_ask_tool_not_available(mock_engine):
    with patch("servers.route.MODELS", [ModelInfo(id="gemini-test", provider="google", name="Gemini", strengths=[], context_window=1000, speed="fast", cost="low")]):
        mock_prov = AsyncMock()
        mock_prov.is_available.return_value = False
        mock_engine.providers = {"google": mock_prov}
        
        result = await ask("gemini-test", "Pregunta")
        assert "not available" in result or "not found" in result

@pytest.mark.asyncio
async def test_compare_tool(mock_engine):
    mock_engine.compare = AsyncMock(return_value={"gemini": "G Response", "groq": "Q Response"})
    result = await compare("Hola", "gemini, groq")
    assert "=== gemini ===" in result
    assert "G Response" in result
    assert "=== groq ===" in result
    assert "Q Response" in result
    mock_engine.compare.assert_called_once_with("Hola", ["gemini", "groq"], temperature=0.7, max_tokens=8192)

@pytest.mark.asyncio
async def test_models_tool(mock_engine):
    mock_engine.get_available_models = AsyncMock(return_value=[
        ModelInfo(id="gemini", provider="google", name="Gemini Pro", strengths=["Code"], context_window=128000, speed="fast", cost="free")
    ])
    result = await models()
    assert "Available Models" in result
    assert "Gemini Pro" in result
    assert "Code" in result

@pytest.mark.asyncio
async def test_classify_task_tool():
    with patch("servers.route.classify", new_callable=AsyncMock) as mock_classify:
        mock_classify.return_value = "code"
        result = await classify_task("Escribe un codigo")
        assert "Detected task type: code" in result
