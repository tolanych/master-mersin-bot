"""
User data management service.
This service delegates to the Database layer which handles caching.
Kept for backward internal API compatibility.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class UserDataService:
    """
    Service for managing user data.
    Delegates caching to Database.
    """
    
    def __init__(self, db_service):
        self.db = db_service
        
    async def get_user_language(self, user_tg_id: int) -> str:
        """
        Get user's preferred language using DB cache.
        """
        try:
            user = await self.db.get_user_by_tg_id(user_tg_id)
            return user.get('language', 'ru') if user else 'ru'
        except Exception as e:
            logger.exception(f"Error getting user language for {user_tg_id}: {e}")
            return 'ru'
    
    async def set_user_language(self, user_tg_id: int, language: str) -> bool:
        """
        Set user's preferred language.
        """
        from config import SUPPORTED_LANGUAGES
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Language must be one of {SUPPORTED_LANGUAGES}")
        
        try:
            user = await self.db.get_user_by_tg_id(user_tg_id)
            if user:
                await self.db.update_user_language(user['id'], language)
                return True
            else:
                logger.warning(f"User {user_tg_id} not found in database")
                return False
        except Exception as e:
            logger.exception(f"Error setting user language for {user_tg_id}: {e}")
            return False
    
    async def get_user_data(self, user_tg_id: int) -> Dict:
        """
        Get complete user data.
        """
        try:
            user = await self.db.get_user_by_tg_id(user_tg_id)
            return user if user else {}
        except Exception as e:
            logger.exception(f"Error getting user data for {user_tg_id}: {e}")
            return {}
    
    async def invalidate_user_cache(self, user_tg_id: int):
        """
        No-op as cache is managed by DB.
        """
        pass
    
    async def clear_cache(self):
        """No-op."""
        pass
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics from DB cache."""
        try:
            return {
                'cached_users': len(self.db.cache.cache)
            }
        except:
            return {}

# Global instance
_user_service = None

def get_user_service() -> Optional[UserDataService]:
    """Get the global user service instance."""
    return _user_service

def init_user_service(db_service) -> UserDataService:
    """Initialize the global user service instance."""
    global _user_service
    _user_service = UserDataService(db_service)
    return _user_service