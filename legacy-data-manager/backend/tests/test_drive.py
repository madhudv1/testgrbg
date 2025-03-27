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

def test_get_auth_url():
    """Test getting the Google OAuth2 authorization URL"""
    response = client.get("/api/v1/drive/auth/url")
    assert response.status_code == 200
    data = response.json()
    assert "auth_url" in data
    assert "google.com" in data["auth_url"]

def test_auth_callback():
    """Test the OAuth2 callback endpoint"""
    # Test with invalid code
    response = client.get("/api/v1/drive/auth/callback?code=invalid_code")
    assert response.status_code == 500  # Should fail with invalid code

def test_auth_status():
    """Test checking authentication status"""
    response = client.get("/api/v1/drive/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert "authenticated" in data
    assert isinstance(data["authenticated"], bool)

def test_list_files():
    """Test listing files"""
    response = client.get("/api/v1/drive/files")
    assert response.status_code in [200, 401]  # Either success or not authenticated
    if response.status_code == 200:
        data = response.json()
        assert "files" in data
        assert isinstance(data["files"], list)

def test_list_inactive_files():
    """Test listing inactive files"""
    response = client.get("/api/v1/drive/files/inactive")
    assert response.status_code in [200, 401]  # Either success or not authenticated
    if response.status_code == 200:
        data = response.json()
        assert "files" in data
        assert isinstance(data["files"], list)

def test_get_file_metadata():
    """Test getting file metadata"""
    # Test with invalid file ID
    response = client.get("/api/v1/drive/files/invalid_file_id")
    assert response.status_code in [404, 401]  # Either not found or not authenticated

def test_get_file_content():
    """Test getting file content"""
    # Test with invalid file ID
    response = client.get("/api/v1/drive/files/invalid_file_id/content")
    assert response.status_code in [404, 401]  # Either not found or not authenticated

def test_update_file_metadata():
    """Test updating file metadata"""
    # Test with invalid file ID
    response = client.put(
        "/api/v1/drive/files/invalid_file_id/metadata",
        json={"name": "new_name"}
    )
    assert response.status_code in [404, 401]  # Either not found or not authenticated

def test_delete_file():
    """Test deleting a file"""
    # Test with invalid file ID
    response = client.delete("/api/v1/drive/files/invalid_file_id")
    assert response.status_code in [404, 401]  # Either not found or not authenticated 