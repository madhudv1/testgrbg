import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from app.services.google_drive import GoogleDriveService

@pytest.fixture
def drive_service():
    """Create a GoogleDriveService instance for testing"""
    return GoogleDriveService()

def test_get_auth_url(drive_service):
    """Test getting the authorization URL"""
    url = drive_service.get_auth_url()
    assert url is not None
    assert isinstance(url, str)
    assert "google.com" in url

def test_get_credentials_from_code(drive_service):
    """Test getting credentials from code"""
    with pytest.raises(Exception):  # Should fail with invalid code
        drive_service.get_credentials_from_code("invalid_code")

def test_is_authenticated(drive_service):
    """Test authentication status check"""
    is_auth = drive_service.is_authenticated()
    assert isinstance(is_auth, bool)

def test_list_files(drive_service):
    """Test listing files"""
    try:
        files = drive_service.list_files(page_size=5)
        assert isinstance(files, list)
        if files:  # If any files are returned
            file = files[0]
            assert "id" in file
            assert "name" in file
            assert "mimeType" in file
            assert "modifiedTime" in file
    except Exception as e:
        # If not authenticated, should raise an exception
        assert "credentials" in str(e).lower()

def test_get_inactive_files(drive_service):
    """Test getting inactive files"""
    try:
        files = drive_service.get_inactive_files()
        assert isinstance(files, list)
        if files:  # If any files are returned
            file = files[0]
            assert "id" in file
            assert "name" in file
            assert "mimeType" in file
            assert "modifiedTime" in file
    except Exception as e:
        # If not authenticated, should raise an exception
        assert "credentials" in str(e).lower()

def test_get_file_metadata(drive_service):
    """Test getting file metadata"""
    with pytest.raises(Exception):  # Should fail with invalid file ID
        drive_service.get_file_metadata("invalid_file_id")

def test_get_file_content(drive_service):
    """Test getting file content"""
    with pytest.raises(Exception):  # Should fail with invalid file ID
        drive_service.get_file_content("invalid_file_id")

def test_update_file_metadata(drive_service):
    """Test updating file metadata"""
    with pytest.raises(Exception):  # Should fail with invalid file ID
        drive_service.update_file_metadata("invalid_file_id", {"name": "new_name"})

def test_delete_file(drive_service):
    """Test deleting a file"""
    with pytest.raises(Exception):  # Should fail with invalid file ID
        drive_service.delete_file("invalid_file_id") 