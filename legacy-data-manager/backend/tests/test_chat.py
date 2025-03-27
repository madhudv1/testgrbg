import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path
import json

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.main import app

client = TestClient(app)

def test_chat_help():
    """Test the help command"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "help"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "help" in data["content"].lower()
    assert "list" in data["content"].lower()
    assert "inactive" in data["content"].lower()
    assert "find" in data["content"].lower()
    assert "status" in data["content"].lower()

def test_chat_status():
    """Test the status command"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "status"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "authenticated" in data["content"].lower()

def test_chat_list():
    """Test the list command"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "list"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    # The response will either show files or indicate not authenticated
    assert any(x in data["content"].lower() for x in ["files", "authenticate"])

def test_chat_inactive():
    """Test the inactive command"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "inactive"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    # The response will either show inactive files or indicate not authenticated
    assert any(x in data["content"].lower() for x in ["inactive", "authenticate"])

def test_chat_find():
    """Test the find command"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "find test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    # The response will either show matching files or indicate not authenticated
    assert any(x in data["content"].lower() for x in ["found", "authenticate"])

def test_chat_find_empty():
    """Test the find command with empty query"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "find"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "provide a search term" in data["content"].lower()

def test_chat_unknown_command():
    """Test unknown command handling"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": "unknown command"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "help" in data["content"].lower()

def test_chat_empty_message():
    """Test empty message handling"""
    response = client.post(
        "/api/v1/chat/message",
        json={"message": ""}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "text"
    assert "help" in data["content"].lower() 