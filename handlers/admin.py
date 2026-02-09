# ================================
# handlers/admin.py — Admin Bulk Moderation
# ================================

import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from typing import Dict, Any

from config import ADMIN_IDS
from utils.i18n import get_text
from keyboards import *
import globals

db = globals.get_db()
bot = globals.get_bot()
router = Router()


async def get_language_from_state(state: FSMContext) -> str:
    """Get language from FSMContext state data"""
    state_data = await state.get_data()
    return state_data.get('language', 'ru')

@router.message(Command("bulk"))
async def cmd_bulk(message: Message, data: Dict[str, Any]):
    state: FSMContext = data.get("state")
    # Language aware responses
    lang = await get_language_from_state(state) if state else 'ru'
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(get_text("permission_denied", lang))
        return

    masters = await db.get_unverified_masters()
    if not masters:
        await message.answer("✅ No unverified masters")
        return

    master = masters[0]
    text = (
        f"🔍 <b>Unverified Master:</b>\n\n"
        f"👤 {master['name']}\n"
        f"📞 {master['phone']}\n"
        f"📍 {', '.join(master['districts'])}\n"
        f"🛠️ {', '.join(master['categories'])}\n\n"
        f"{master['description']}"
    )
    await message.answer(text, reply_markup=get_admin_approve_reject_keyboard(master['id'], lang))

@router.callback_query(F.data.startswith("admin_approve_"))
async def admin_approve(callback: CallbackQuery, state: FSMContext, data: Dict[str, Any]):
    master_id = int(callback.data.split("_")[2])
    await db.approve_master(master_id)

    try:
        master = await db.get_master(master_id)
        if master:
            master_user = await db.get_user(master['user_id'])
            if master_user:
                lang = await get_language_from_state(state)
                await bot.send_message(master_user['tg_id'], get_text("master_onboarding", lang))
                await bot.send_message(master_user['tg_id'], get_text("master_how_more", lang))
    except Exception:
        pass

    await callback.message.edit_text(get_text("master_onboarding", lang) if lang else "✅ Master approved!")

@router.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject(callback: CallbackQuery, state: FSMContext, data: Dict[str, Any]):
    master_id = int(callback.data.split("_")[2])
    await db.reject_master(master_id)
    lang = await get_language_from_state(state)
    await callback.message.edit_text(get_text("master_registration_cancelled", lang))

@router.message(Command("debug_db"))
async def debug_db(message: Message, data: Dict[str, Any]):
    state: FSMContext = data.get("state")
    admins = set(map(int, os.getenv("ADMINS","").split(","))) if os.getenv("ADMINS") else set()
    if admins and message.from_user.id not in admins:
        return

    db = message.bot['db']
    info = db.debug_info()
    await message.answer("\n".join(f"{k}: {v}" for k,v in info.items()))
