# ================================
# main.py — Dispatcher & Webhook Setup (FIXED)
# ================================

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
import uvicorn

from aiogram import Dispatcher, Bot
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import Update, BotCommand, BotCommandScopeDefault
from aiogram.fsm.storage.memory import MemoryStorage

from middlewares.order_check import OrderCheckMiddleware

from config import BOT_TOKEN, WEBHOOK_URL, ADMIN_IDS, PORT
import config
from database import Database
from services.user_service import init_user_service
from services.cache_service import CacheService
import globals  # Import globals FIRST (before handlers)

async def sync_config_with_db(db: Database):
    """Synchronize config.py variables with current database state"""
    try:
        # Load Districts
        dists = await db.get_districts()
        if dists:
            config.DISTRICTS[:] = [d['key_field'] for d in dists]
            
        # Load Categories (All categories for general key access)
        all_cats = await db.get_all_categories()
        if all_cats:
            config.CATEGORIES[:] = [c['key_field'] for c in all_cats]
            
            # CATEGORY_GROUPS is now legacy but we can populate it with root parents for safety
            config.CATEGORY_GROUPS.clear()
            roots = [c for c in all_cats if c['parent_id'] is None]
            for r in roots:
                config.CATEGORY_GROUPS[r['key_field']] = [] # Empty list as we use dynamic navigation
                
        logger.info(f"⚙️ Config synced with DB: {len(config.CATEGORIES)} categories, {len(config.DISTRICTS)} districts")
    except Exception as e:
        logger.error(f"❌ Failed to sync config with DB: {e}")

# ====== Logging ======
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== Initialize storage & dispatcher ======
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Register Middlewares
dp.message.middleware(OrderCheckMiddleware())
dp.callback_query.middleware(OrderCheckMiddleware())

# ====== FastAPI app (for Render webhook) ======
app = FastAPI(title="Mersin Masters Bot")

# ====== Startup/Shutdown ======
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events"""
    # Startup
    logger.info("🚀 Bot starting...")
    
    # Initialize database (async init)
    globals.db = Database(config.DATABASE_URL)
    await globals.db.init()
    
    # Initialize user service
    globals.user_service = init_user_service(globals.db)
    
    # Sync config with database data
    await sync_config_with_db(globals.db)
    
    # Initialize cache service
    globals.cache_service = CacheService()
    await globals.cache_service.load(globals.db)
    
    # Initialize bot
    globals.bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    
    # NOW import handlers (after globals initialized)
    from handlers import client, master, add_master, admin, payments, premium
    
    # Register handlers
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(add_master.router)
    dp.include_router(admin.router)
    dp.include_router(payments.router)
    dp.include_router(premium.router)
    
    # Set bot commands
    commands = [
        BotCommand(command="start", description="Запуск / Başla"),
        BotCommand(command="profile", description="Профиль / Profil"),
        BotCommand(command="lang", description="Язык / Dil"),
    ]
    await globals.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    # Set webhook (if WEBHOOK_URL is set)
    if WEBHOOK_URL:
        try:
            await globals.bot.set_webhook(
                url=f"{WEBHOOK_URL}/webhook",
                allowed_updates=["message", "callback_query", "my_chat_member"]
            )
            logger.info(f"✅ Webhook set: {WEBHOOK_URL}/webhook")
        except Exception as e:
            logger.error(f"❌ Webhook error: {e}")
    else:
        logger.info("⚠️  WEBHOOK_URL not set, using polling (for local dev)")
    
    yield
    
    # Shutdown
    logger.info("🛑 Bot shutting down...")
    await globals.bot.session.close()
    await globals.db.close()

app.router.lifespan_context = lifespan

# ====== Webhook endpoint ======
@app.post("/webhook")
async def webhook(request: Request):
    """Telegram webhook handler"""
    try:
        update_data = await request.json()
        update = Update(**update_data)
        await dp.feed_update(globals.bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"ok": False, "error": str(e)}

# ====== Health check ======
@app.get("/health")
async def health_check():
    """Health check for UptimeRobot"""
    return {"status": "ok"}

# ====== Dev stats (Memory) ======
@app.get("/dev")
async def dev_stats():
    """Hook for memory diagnostics"""
    from utils.memory_utils import get_size, get_process_memory
    import psutil
    import os

    # Measure caches
    cat_size = 0
    dist_size = 0
    user_cache_size = 0
    process = psutil.Process(os.getpid())

    if globals.cache_service:
        cat_size = get_size(globals.cache_service.categories)
        dist_size = get_size(globals.cache_service.districts)
        
    if globals.db and hasattr(globals.db, 'cache'):
        user_cache_size = get_size(globals.db.cache.cache)
    
    total_cache_kb = (cat_size + dist_size + user_cache_size) / 1024
    
    return {
        "cache_memory_kb": round(total_cache_kb, 2),
        "process_memory": f"RAM: {process.memory_info().rss / 1024**2:.1f} MB",
        "cpu": f"CPU %: {process.cpu_percent()}",
        "details": {
            "categories_cache_kb": round(cat_size / 1024, 2),
            "districts_cache_kb": round(dist_size / 1024, 2),
            "user_cache_kb": round(user_cache_size / 1024, 2)
        }
    }

# ====== Local polling (for development) ======
async def run_polling():
    """Run bot with long polling (for local testing)"""
    logger.info("🚀 Bot starting (polling mode)...")
    
    # Initialize database (async init)
    globals.db = Database(config.DATABASE_URL)
    await globals.db.init()
    
    # Initialize user service
    globals.user_service = init_user_service(globals.db)
    
    # Sync config with database data
    await sync_config_with_db(globals.db)
    
    # Initialize cache service
    globals.cache_service = CacheService()
    await globals.cache_service.load(globals.db)
    
    # Initialize bot
    globals.bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    
    # NOW import handlers (after globals initialized)
    from handlers import client, master, add_master, admin, payments, premium
    
    # Register handlers
    dp.include_router(client.router)
    dp.include_router(master.router)
    dp.include_router(add_master.router)
    dp.include_router(admin.router)
    dp.include_router(payments.router)
    dp.include_router(premium.router)
    
    # Set bot commands
    commands = [
        BotCommand(command="start", description="Запуск / Başla"),
        BotCommand(command="profile", description="Профиль / Profil"),
        BotCommand(command="lang", description="Язык / Dil"),
    ]
    await globals.bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    # Ensure webhook is removed
    await globals.bot.delete_webhook(drop_pending_updates=True)
    logger.info("🗑️ Webhook removed")

    try:
        await dp.start_polling(globals.bot)
    finally:
        await globals.bot.session.close()
        await globals.db.close()

# ====== Entry point ======
def generate_self_signed_cert(cert_path, key_path):
    import subprocess
    import os
    
    os.makedirs(os.path.dirname(cert_path), exist_ok=True)
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        logger.info("🔐 Generating self-signed SSL certificates...")
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096", 
                "-keyout", key_path, "-out", cert_path, 
                "-days", "365", "-nodes", 
                "-subj", "/C=TR/ST=Mersin/L=Mersin/O=MersinMasters/OU=Bot/CN=localhost"
            ], check=True)
            logger.info(f"✅ Certificates generated: {cert_path}, {key_path}")
        except Exception as e:
            logger.error(f"❌ Failed to generate certificates: {e}")

if __name__ == "__main__":
    import os
    
    if os.getenv("USE_POLLING") == "true":
        # Local development
        logger.info("📱 Running in POLLING mode (local)")
        asyncio.run(run_polling())
    else:
        # Webhook mode (Docker/Render)
        logger.info("🌐 Running in WEBHOOK mode")
        
        cert_path = os.getenv("SSL_CERT_PATH", "./certs/cert.pem")
        key_path = os.getenv("SSL_KEY_PATH", "./certs/key.pem")
        
        # Generate certs if they don't exist
        generate_self_signed_cert(cert_path, key_path)
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level="info",
            ssl_keyfile=key_path, 
            ssl_certfile=cert_path
        )