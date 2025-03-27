import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.main import app

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app) 