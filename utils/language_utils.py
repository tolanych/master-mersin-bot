"""
Language utilities that work independently of FSM states.
These functions provide consistent language access using the user service.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

async def get_user_language(user_tg_id: int) -> str:
    """
    Get user's preferred language using user service.
    
    Args:
        user_tg_id: Telegram user ID
        
    Returns:
        Language code ('ru' or 'tr'), defaults to 'ru'
    """
    try:
        from services.user_service import get_user_service
        user_service = get_user_service()
        
        if user_service:
            return await user_service.get_user_language(user_tg_id)
        else:
            # Fallback to database if service not available
            import globals
            if globals.db:
                user = await globals.db.get_user_by_tg_id(user_tg_id)
                return user.get('language', 'ru') if user else 'ru'
            return 'ru'
    except Exception as e:
        logger.exception(f"Error getting user language for {user_tg_id}: {e}")
        return 'ru'  # Default fallback

async def set_user_language(user_tg_id: int, language: str) -> bool:
    """
    Set user's preferred language using user service.
    
    Args:
        user_tg_id: Telegram user ID
        language: Language code ('ru' or 'tr')
        
    Returns:
        True if successful, False otherwise
    """
    from config import SUPPORTED_LANGUAGES
    if language not in SUPPORTED_LANGUAGES:
        # For now, just warn and fallback or raise
        # But since I added 'en' to SUPPORTED_LANGUAGES in config.py, this is safe.
        raise ValueError(f"Language must be one of {SUPPORTED_LANGUAGES}")
    
    try:
        from services.user_service import get_user_service
        user_service = get_user_service()
        
        if user_service:
            return await user_service.set_user_language(user_tg_id, language)
        else:
            # Fallback to database if service not available
            import globals
            if globals.db:
                user = await globals.db.get_user_by_tg_id(user_tg_id)
                if user:
                    await globals.db.update_user_language(user['id'], language)
                    return True
            return False
    except Exception as e:
        logger.exception(f"Error setting user language for {user_tg_id}: {e}")
        return False

def get_text(key: str, lang: str = 'ru') -> str:
    """
    Get localized text by key and language.
    
    Args:
        key: Text key
        lang: Language code ('ru' or 'tr')
        
    Returns:
        Localized text
    """
    from utils.i18n import get_text as i18n_get_text
    return i18n_get_text(key, lang)