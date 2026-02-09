# ================================
# handlers/payments.py — Payment Placeholders (Stripe/Yookassa)
# ================================

from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from typing import Dict, Any

from config import ENABLE_PAYMENTS
import globals

db = globals.get_db()
bot = globals.get_bot()

router = Router()

@router.message(Command("premium"))
async def cmd_premium(message: Message, data: Dict[str, Any]):
    """Premium subscription (placeholder)"""
    state: FSMContext = data.get("state")
    if not ENABLE_PAYMENTS:
        await message.answer("❌ Premium feature not available yet")
        return
    
    # TODO: Implement Stripe/Yookassa payment link
    text = "📌 <b>Premium Subscription</b>\n\n💰 30 days: 100₺\n\n✨ Features:\n• Top placement in search\n• No ads\n• Priority support\n\nClick below to subscribe:"
    
    await message.answer(text)
