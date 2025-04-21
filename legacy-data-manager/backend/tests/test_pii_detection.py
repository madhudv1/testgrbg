import asyncio
import os
from datetime import datetime
import pytest
from app.services.pii_detector import PIIDetector
from app.services.rate_limiter import LLMRateLimiter

@pytest.fixture
def pii_detector():
    return PIIDetector()

@pytest.fixture
def rate_limiter():
    return LLMRateLimiter()

@pytest.mark.asyncio
async def test_pii_detection_small_file(pii_detector):
    # Read test file
    with open('tests/test_files/test1.txt', 'r') as f:
        content = f.read()
    
    # Test single file scan
    result = await pii_detector.scan_file(
        file_id='test1',
        content=content,
        file_size=len(content.encode('utf-8'))
    )
    
    assert result is not None
    assert 'email' in result['pii_types']
    assert 'phone' in result['pii_types']
    assert result['pii_types']['email']['count'] == 3
    assert result['pii_types']['phone']['count'] == 3
    assert result['scan_coverage'] == 1.0  # Should be 100% for small file

@pytest.mark.asyncio
async def test_rate_limiter(rate_limiter):
    user_id = 'test_user'
    
    # Test initial state
    status = await rate_limiter.get_status(user_id)
    assert status['available_tokens'] == 10000
    assert status['available_requests'] == 500
    
    # Test token acquisition
    success = await rate_limiter.acquire(user_id, tokens=100)
    assert success is True
    
    # Test status after acquisition
    status = await rate_limiter.get_status(user_id)
    assert status['available_tokens'] == 9900
    assert status['available_requests'] == 499
    assert status['user_tokens_used'] == 100
    assert status['user_requests_used'] == 1

@pytest.mark.asyncio
async def test_parallel_processing(pii_detector):
    # Create multiple test files
    files = [
        {
            'id': 'test1',
            'content': open('tests/test_files/test1.txt', 'r').read(),
            'size': os.path.getsize('tests/test_files/test1.txt')
        },
        {
            'id': 'test2',
            'content': open('tests/test_files/test2.txt', 'r').read(),
            'size': os.path.getsize('tests/test_files/test2.txt')
        }
    ]
    
    # Test parallel scanning
    results = await pii_detector.scan_files(files)
    
    assert results['total_files'] == 2
    assert results['processed_files'] == 2
    assert results['failed_files'] == 0
    assert len(results['results']) == 2

@pytest.mark.asyncio
async def test_rate_limit_exceeded(rate_limiter):
    user_id = 'test_user'
    
    # Try to acquire more tokens than the per-minute limit
    success = await rate_limiter.acquire(user_id, tokens=11000)
    assert success is False
    
    # Try to acquire more requests than the per-minute limit
    for _ in range(501):
        success = await rate_limiter.acquire(user_id, tokens=1)
        if not success:
            break
    
    status = await rate_limiter.get_status(user_id)
    assert status['user_requests_used'] < 501  # Should not exceed limit 