from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import logging

logger = logging.getLogger(__name__)

class ScanCacheService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScanCacheService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.cache = {
            'drive': {
                'last_scan': None,
                'data': None
            },
            'directories': {}
        }
        self.cache_ttl = timedelta(minutes=60)
        self._initialized = True

    def get_cached_result(self, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached scan result for a target (drive or directory).
        Returns None if no cache exists or if cache is expired.
        """
        try:
            if target_id == 'drive':
                cache_entry = self.cache['drive']
            else:
                cache_entry = self.cache['directories'].get(target_id)

            if not cache_entry or not cache_entry['last_scan']:
                return None

            # Check if cache is expired
            if datetime.utcnow() - cache_entry['last_scan'] > self.cache_ttl:
                logger.info(f"Cache expired for {target_id}")
                return None

            logger.info(f"Using cached result for {target_id}")
            return cache_entry['data']

        except Exception as e:
            logger.error(f"Error getting cached result: {str(e)}", exc_info=True)
            return None

    def update_cache(self, target_id: str, data: Dict[str, Any]) -> None:
        """
        Update cache with new scan result.
        """
        try:
            if target_id == 'drive':
                self.cache['drive'] = {
                    'last_scan': datetime.utcnow(),
                    'data': data
                }
            else:
                self.cache['directories'][target_id] = {
                    'last_scan': datetime.utcnow(),
                    'data': data
                }
            logger.info(f"Updated cache for {target_id}")
        except Exception as e:
            logger.error(f"Error updating cache: {str(e)}", exc_info=True)

    def invalidate_cache(self, target_id: Optional[str] = None) -> None:
        """
        Invalidate cache for a specific target or all targets.
        If target_id is None, invalidate all caches.
        """
        try:
            if target_id is None:
                # Invalidate all caches
                self.cache['drive'] = {'last_scan': None, 'data': None}
                self.cache['directories'] = {}
                logger.info("Invalidated all caches")
            elif target_id == 'drive':
                self.cache['drive'] = {'last_scan': None, 'data': None}
                logger.info("Invalidated drive cache")
            else:
                self.cache['directories'].pop(target_id, None)
                logger.info(f"Invalidated cache for directory {target_id}")
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}", exc_info=True)

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status.
        """
        try:
            status = {
                'drive': {
                    'cached': self.cache['drive']['last_scan'] is not None,
                    'last_scan': self.cache['drive']['last_scan'].isoformat() if self.cache['drive']['last_scan'] else None
                },
                'directories': {}
            }

            for dir_id, cache_entry in self.cache['directories'].items():
                status['directories'][dir_id] = {
                    'cached': cache_entry['last_scan'] is not None,
                    'last_scan': cache_entry['last_scan'].isoformat() if cache_entry['last_scan'] else None
                }

            return status
        except Exception as e:
            logger.error(f"Error getting cache status: {str(e)}", exc_info=True)
            return {'error': str(e)}

    def get_cached_directories(self) -> List[str]:
        """
        Get list of directory IDs that are currently cached.
        """
        return list(self.cache['directories'].keys())

    def is_cached(self, target_id: str) -> bool:
        """
        Check if a target is currently cached and not expired.
        """
        return self.get_cached_result(target_id) is not None 

    def get_cache_entry(self, target_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full cache entry including metadata for a target (drive or directory).
        Returns None if no cache exists.
        """
        try:
            if target_id == 'drive':
                return self.cache['drive']
            else:
                return self.cache['directories'].get(target_id)
        except Exception as e:
            logger.error(f"Error getting cache entry: {str(e)}", exc_info=True)
            return None 