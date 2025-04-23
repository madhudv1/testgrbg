from typing import Dict, List, Tuple
import re
import time
from datetime import datetime, timedelta

class RuleBasedClassifier:
    def __init__(self):
        # Patterns that might indicate sensitive content
        self.patterns = {
            'pii': [
                r'hr', r'employee', r'personnel', r'salary', r'resume', 
                r'cv', r'personal', r'contact', r'address'
            ],
            'financial': [
                r'finance', r'budget', r'revenue', r'expense', r'invoice',
                r'payment', r'bank', r'account', r'tax', r'profit'
            ],
            'legal': [
                r'contract', r'agreement', r'legal', r'policy', r'compliance',
                r'terms', r'nda', r'confidential'
            ],
            'confidential': [
                r'private', r'secret', r'internal', r'confidential',
                r'proprietary', r'restricted'
            ]
        }
        
        # Rate limiting settings
        self.rate_limit = 50  # requests per hour
        self.request_timestamps = []
        
        # Compile all patterns
        self.compiled_patterns = {
            category: [re.compile(pattern, re.IGNORECASE) 
                      for pattern in patterns]
            for category, patterns in self.patterns.items()
        }

        # Image MIME types that we can analyze
        self.image_mime_types = [
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/bmp',
            'image/webp',
            'application/vnd.google-apps.drawing'
        ]

    def _check_rate_limit(self) -> bool:
        """Check if we've hit the rate limit"""
        now = datetime.now()
        # Remove timestamps older than 1 hour
        self.request_timestamps = [ts for ts in self.request_timestamps 
                                 if now - ts < timedelta(hours=1)]
        return len(self.request_timestamps) < self.rate_limit

    def _record_request(self):
        """Record a new request timestamp"""
        self.request_timestamps.append(datetime.now())

    async def analyze_document(self, filename: str, mime_type: str, content: bytes = None) -> Dict:
        """
        Analyze a document based on its filename, mime type, and content if available.
        Returns a dict with confidence score and matched categories.
        """
        # First check filename patterns
        matches = []
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(filename):
                    matches.append((category, 0.8))  # Conservative confidence score
                    break

        # Check if this is an image that needs LLM analysis
        is_image = mime_type in self.image_mime_types
        needs_llm = is_image and content and self._check_rate_limit()

        if needs_llm:
            try:
                self._record_request()
                # TODO: Implement actual LLM analysis here
                # For now, mark all images as potentially sensitive
                if not matches:
                    matches.append(('confidential', 0.6))
            except Exception as e:
                # Log the error but continue with pattern-based analysis
                print(f"Error in LLM analysis: {e}")
                
        # If no matches found but it's a document type that typically contains sensitive info
        sensitive_mime_types = [
            'application/vnd.google-apps.document',
            'application/vnd.google-apps.spreadsheet',
            'application/pdf'
        ] + self.image_mime_types
        
        if not matches and mime_type in sensitive_mime_types:
            matches.append(('confidential', 0.6))  # Lower confidence for mime-type only

        if not matches:
            return {
                'confidence_score': 0,
                'explanation': 'No sensitive patterns detected',
                'key_topics': [],
                'primary_category': None,
                'queued_for_analysis': is_image and not self._check_rate_limit()
            }

        # Get highest confidence match
        primary_match = max(matches, key=lambda x: x[1])
        
        return {
            'confidence_score': primary_match[1],
            'explanation': f'Matched patterns for category: {primary_match[0]}',
            'key_topics': [m[0] for m in matches],
            'primary_category': self._map_category_to_primary(primary_match[0]),
            'queued_for_analysis': is_image and not self._check_rate_limit()
        }

    def _map_category_to_primary(self, category: str) -> str:
        """Map internal categories to primary categories used by the frontend"""
        mapping = {
            'pii': 'HR Documents',
            'financial': 'Financial Documents',
            'legal': 'Legal Documents',
            'confidential': 'Technical Documents'
        }
        return mapping.get(category, 'Other Documents') 