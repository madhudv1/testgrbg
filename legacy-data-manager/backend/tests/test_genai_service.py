import pytest
from app.services.genai_service import GenAIService
from app.core.config import settings

def test_genai_service_initialization():
    """Test that the GenAI service can be initialized with the token."""
    try:
        service = GenAIService()
        assert service.client is not None
        assert service.model == "mistralai/Mixtral-8x7B-Instruct-v0.1"
    except Exception as e:
        pytest.fail(f"Failed to initialize GenAI service: {str(e)}")

def test_genai_service_token():
    """Test that the Hugging Face token is valid."""
    try:
        service = GenAIService()
        # Try a simple test prompt
        response = service.client.text_generation(
            "Hello, this is a test.",
            model=service.model,
            max_new_tokens=10
        )
        assert response is not None
        assert len(response) > 0
    except Exception as e:
        pytest.fail(f"Failed to use Hugging Face token: {str(e)}") 