from datetime import datetime
import asyncio
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class LLMRateLimiter:
    def __init__(self):
        # More realistic limits based on OpenAI's GPT-3.5
        self.tokens_per_minute = 10000  # 10K TPM
        self.requests_per_minute = 500   # 500 RPM
        self.max_bucket_size = self.tokens_per_minute  # Maximum token bucket size
        self.max_request_bucket_size = self.requests_per_minute  # Maximum request bucket size
        
        # Current token and request counts
        self.tokens = self.max_bucket_size
        self.requests = self.max_request_bucket_size
        
        self.last_refill = datetime.now()
        self.lock = asyncio.Lock()
        
        # Track usage per user/directory
        self.user_tokens = defaultdict(int)
        self.user_requests = defaultdict(int)
        
        # Soft limits per user (80% of total)
        self.user_token_limit = int(self.tokens_per_minute * 0.8)
        self.user_request_limit = int(self.requests_per_minute * 0.8)

    async def can_process(self, user_id: str, tokens: int = 1) -> bool:
        """Check if we can process a request with given token count."""
        async with self.lock:
            await self._refill()
            
            # Check global limits
            if self.tokens < tokens or self.requests < 1:
                logger.warning(f"Rate limit reached. Tokens: {self.tokens}, Requests: {self.requests}")
                return False
            
            # Check user limits
            if (self.user_tokens[user_id] + tokens > self.user_token_limit or 
                self.user_requests[user_id] + 1 > self.user_request_limit):
                logger.warning(f"User rate limit reached for {user_id}")
                return False
            
            return True

    async def acquire(self, user_id: str, tokens: int = 1) -> bool:
        """Acquire tokens and a request slot."""
        async with self.lock:
            if not await self.can_process(user_id, tokens):
                return False
            
            # Update counts
            self.tokens -= tokens
            self.requests -= 1
            self.user_tokens[user_id] += tokens
            self.user_requests[user_id] += 1
            
            return True

    async def _refill(self):
        """Refill tokens and requests based on time passed."""
        now = datetime.now()
        time_passed = (now - self.last_refill).total_seconds()
        
        # Calculate new tokens and requests
        new_tokens = int(time_passed * (self.tokens_per_minute / 60))
        new_requests = int(time_passed * (self.requests_per_minute / 60))
        
        # Update tokens and requests
        self.tokens = min(self.max_bucket_size, self.tokens + new_tokens)
        self.requests = min(self.max_request_bucket_size, self.requests + new_requests)
        
        # Reset user counts periodically (every minute)
        if time_passed >= 60:
            self.user_tokens.clear()
            self.user_requests.clear()
        
        self.last_refill = now

    async def get_status(self, user_id: str) -> dict:
        """Get current rate limit status."""
        async with self.lock:
            await self._refill()
            return {
                "available_tokens": self.tokens,
                "available_requests": self.requests,
                "user_tokens_used": self.user_tokens[user_id],
                "user_requests_used": self.user_requests[user_id],
                "user_token_limit": self.user_token_limit,
                "user_request_limit": self.user_request_limit
            } 