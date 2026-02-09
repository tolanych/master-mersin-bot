# ================================
# globals.py — Global Instances (db, bot)
# ================================

from typing import Optional
from aiogram import Bot
from database import Database

# These will be initialized in main.py startup
bot: Optional[Bot] = None
db: Optional[Database] = None
# Service singletons
user_service = None
cache_service = None

def get_bot() -> Bot:
    """Get bot instance"""
    if bot is None:
        raise RuntimeError("Bot not initialized yet")
    return bot

def get_db() -> Database:
    """Get database instance"""
    if db is None:
        raise RuntimeError("Database not initialized yet")
    return db