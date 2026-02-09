# ================================
# handlers/premium.py — Premium Status Flow
# ================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import globals
from config import ADMIN_IDS
from states import MasterPremium
from keyboards import get_premium_keyboard, get_main_menu_keyboard
from utils.i18n import get_text
from services.stickers import replace_sticker, StickerEvent, clear_state_preserve_sticker


db = globals.get_db()
bot = globals.get_bot()

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(F.data == "menu_premium")
async def menu_premium(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show premium status information"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    try:
        await replace_sticker(callback.message, state, StickerEvent.PREMIUM)
        await callback.message.delete()
        should_resend = True
    except Exception as e:
        logger.warning(f"Failed to replace sticker in premium: {e}")
        should_resend = False

    if not user:
        await callback.answer(get_text("error", lang))
        return

    master = await db.get_master_by_user_id(user['id'])
    if not master:
        await callback.answer(get_text("error", lang))
        return

    is_premium = master.get('status') == 'active_premium'
    
    text = get_text("premium_title", lang) + "\n\n"
    
    if is_premium:
        premium_until = master.get('premium_until', '-')
        # Format date if possible
        if premium_until and 'T' in premium_until:
            date_str = premium_until.split('T')[0]
        else:
            date_str = premium_until
        
        text += get_text("premium_active_until", lang, date=date_str) + "\n\n"
    
    text += get_text("premium_info", lang)
    
    markup = get_premium_keyboard(lang, is_active=is_premium)
    if should_resend:
        await callback.message.answer(text, reply_markup=markup, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    
    await clear_state_preserve_sticker(state)

@router.callback_query(F.data == "premium_buy")
async def premium_buy(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show payment details"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    text = get_text("premium_buy_info", lang, user_id=user['id'])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_i_paid", lang), callback_data="premium_i_paid")],
            [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="menu_premium")]
        ]),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "premium_i_paid")
async def premium_i_paid(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Ask for screenshot"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    text = get_text("premium_technical_issues", lang) + "\n\n" + ("Пожалуйста, отправьте скриншот или PDF-файл оплаты." if lang == 'ru' else "Lütfen ödeme dekontunu veya PDF dosyasını gönderin.")
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="menu_premium")]
        ])
    )
    # Record request in DB
    master = await db.get_master_by_user_id(user['id'])
    if master:
        await db.add_premium_request(master['id'], user['id'], "pending")

    await state.set_state(MasterPremium.waiting_screenshot)

@router.message(MasterPremium.waiting_screenshot, F.photo | F.document)
async def process_premium_payment_proof(message: Message, state: FSMContext, user: dict = None):
    """Receive screenshot/PDF and notify admins"""
    lang = user.get('language', 'ru') if user else 'ru'
    master = await db.get_master_by_user_id(user['id'])
    
    file_id = None
    is_photo = False
    
    if message.photo:
        file_id = message.photo[-1].file_id
        is_photo = True
    elif message.document:
        file_id = message.document.file_id
    
    if not file_id:
        await message.answer(get_text("error", lang))
        return

    # Record request in DB
    await db.add_premium_request(master['id'], user['id'], "screenshot")

    # Notify admins
    caption = get_text("admin_premium_payment", "ru", 
                       name=master['name'], 
                       user_id=user['id'], 
                       phone=master['phone'])

    for admin_id in ADMIN_IDS:
        try:
            if is_photo:
                await bot.send_photo(
                    admin_id,
                    file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
            else:
                await bot.send_document(
                    admin_id,
                    file_id,
                    caption=caption,
                    parse_mode="HTML"
                )
        except Exception:
            logger.exception(f"Failed to send payment proof to admin {admin_id}")

    await message.answer(get_text("premium_screenshot_sent", lang))
    
    # Return to main menu
    await replace_sticker(message, state, StickerEvent.CATEGORIES)
    await message.answer(
        get_text("main_menu", lang), 
        reply_markup=await get_main_menu_keyboard(user=user)
    )
    await clear_state_preserve_sticker(state)

@router.message(MasterPremium.waiting_screenshot)
async def process_premium_non_proof(message: Message, state: FSMContext, user: dict = None):
    """Handle non-proof messages when waiting for payment proof"""
    lang = user.get('language', 'ru') if user else 'ru'
    if message.text and message.text.lower() in ["назад", "back", "geri", "↩️ назад"]:
        await replace_sticker(message, state, StickerEvent.CATEGORIES)
        await message.answer(
            get_text("main_menu", lang), 
            reply_markup=await get_main_menu_keyboard(user=user)
        )
        await clear_state_preserve_sticker(state)
        return

    await replace_sticker(message, state, StickerEvent.CATEGORIES)
    await message.answer(get_text("premium_payment_ftype", lang), reply_markup=await get_main_menu_keyboard(user=user))
