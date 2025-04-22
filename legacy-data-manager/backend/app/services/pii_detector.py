import asyncio
import random
from datetime import datetime
import logging
from typing import Dict, List, Optional
import re

logger = logging.getLogger(__name__)

class ScanError(Exception):
    def __init__(self, file_id: str, error_type: str, message: str):
        self.file_id = file_id
        self.error_type = error_type
        self.message = message
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)

class PIIDetector:
    def __init__(self):
        # Concurrency settings
        self.max_concurrent_files = 5
        self.file_timeout = 30  # seconds
        self.semaphore = asyncio.Semaphore(self.max_concurrent_files)
        
        # Sampling thresholds (in bytes)
        self.sampling_thresholds = {
            1_000_000: 1.0,      # 100% for files < 1MB
            10_000_000: 0.5,     # 50% for files 1-10MB
            float('inf'): 0.25   # 25% for files > 10MB
        }
        
        # PII patterns
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'ssn': r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b',
            'phone': r'\b(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
            'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        }
        
        # Error tracking
        self.errors: List[Dict] = []

    def _get_sampling_rate(self, file_size: int) -> float:
        """Determine sampling rate based on file size."""
        for threshold, rate in sorted(self.sampling_thresholds.items()):
            if file_size <= threshold:
                return rate
        return self.sampling_thresholds[float('inf')]

    def _sample_content(self, content: str, sampling_rate: float) -> str:
        """Randomly sample content based on sampling rate."""
        if sampling_rate >= 1.0:
            return content
            
        content_length = len(content)
        sample_size = int(content_length * sampling_rate)
        
        # Generate random indices
        indices = sorted(random.sample(range(content_length), sample_size))
        
        # Sample the content
        return ''.join(content[i] for i in indices)

    async def scan_file(self, file_id: str, content: str, file_size: int) -> Dict:
        """Scan a single file for PII."""
        try:
            # Determine sampling rate and sample content
            sampling_rate = self._get_sampling_rate(file_size)
            sampled_content = self._sample_content(content, sampling_rate)
            
            results = {
                'file_id': file_id,
                'scan_coverage': sampling_rate,
                'pii_types': {},
                'scan_timestamp': datetime.utcnow().isoformat()
            }
            
            # Scan for each PII type
            for pii_type, pattern in self.patterns.items():
                matches = re.finditer(pattern, sampled_content, re.IGNORECASE)
                count = sum(1 for _ in matches)
                
                if count > 0:
                    results['pii_types'][pii_type] = {
                        'count': count,
                        'confidence': 0.95 if pii_type in ['ssn', 'credit_card'] else 0.85
                    }
            
            return results
            
        except Exception as e:
            error = ScanError(file_id, 'scan_error', str(e))
            self._log_error(error)
            return None

    async def scan_files(self, files: List[Dict]) -> Dict:
        """Scan multiple files in parallel."""
        async def _scan_file_with_timeout(file: Dict) -> Optional[Dict]:
            try:
                async with self.semaphore:
                    return await asyncio.wait_for(
                        self.scan_file(
                            file['id'],
                            file.get('content', ''),
                            int(file.get('size', 0))
                        ),
                        timeout=self.file_timeout
                    )
            except asyncio.TimeoutError:
                error = ScanError(
                    file['id'],
                    'timeout',
                    f"Scan timeout after {self.file_timeout} seconds"
                )
                self._log_error(error)
                return None
            except Exception as e:
                error = ScanError(file['id'], 'processing_error', str(e))
                self._log_error(error)
                return None

        # Process files in parallel
        tasks = [_scan_file_with_timeout(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        # Aggregate results
        return {
            'scan_timestamp': datetime.utcnow().isoformat(),
            'total_files': len(files),
            'processed_files': len([r for r in results if r is not None]),
            'failed_files': len([r for r in results if r is None]),
            'results': [r for r in results if r is not None],
            'errors': self.errors
        }

    def _log_error(self, error: ScanError):
        """Log scan errors."""
        error_entry = {
            'timestamp': error.timestamp.isoformat(),
            'file_id': error.file_id,
            'error_type': error.error_type,
            'message': error.message
        }
        self.errors.append(error_entry)
        logger.error(f"Scan error: {error_entry}")

    def get_error_summary(self) -> Dict:
        """Get summary of scanning errors."""
        return {
            'total_errors': len(self.errors),
            'error_types': {
                error_type: len([e for e in self.errors if e['error_type'] == error_type])
                for error_type in set(e['error_type'] for e in self.errors)
            },
            'errors': self.errors[-10:]  # Return last 10 errors
        } 