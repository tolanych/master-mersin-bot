# ================================
# handlers/client.py — Client Commands & Flows
# ================================

import logging
from typing import Union


from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram import flags


from config import DISTRICTS, CATEGORIES, ADMIN_IDS, MODERATOR_USERNAME
from states import ClientSearch, ClientFindMaster, ClientConcierge, ClientReview, ClientAddMaster, ClientPhoneVerification, ClientChangePhone, ClientReport
import globals
from utils.language_utils import set_user_language
from keyboards import (
    get_language_keyboard,
    get_main_menu_keyboard,
    get_categories_keyboard_v2,
    get_client_districts_keyboard,
    get_urgency_keyboard,
    get_budget_keyboard,
    get_concierge_topics_keyboard,
    get_districts_keyboard,
    get_categories_keyboard,
    get_masters_keyboard,
    get_master_districts_keyboard,
    get_master_profile_keyboard,
    get_order_completion_keyboard,
    get_rating_keyboard,
    get_add_master_keyboard,
    get_request_submitted_keyboard,
    get_share_phone_keyboard,
    get_remove_keyboard,
    get_client_profile_keyboard,
    get_master_own_profile_keyboard,
    get_client_master_feedback_checklist_keyboard,
    get_skip_feedback_keyboard,
    get_orders_menu_keyboard,
    get_orders_history_keyboard
)
from utils.i18n import get_text, get_category_name, get_district_name
from utils.phone_utils import normalize_phone, is_valid_phone
from services.stickers import replace_sticker, StickerEvent, clear_state_preserve_sticker

db = globals.get_db()
bot = globals.get_bot()

logger = logging.getLogger(__name__)
router = Router()





# ====== START / ROLE SELECTION ======
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, user: dict = None):
    """Start command - language choose (first time) → main menu"""
    # Create user as client by default (is_client=1, is_master=0)
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    lang = user.get('language', 'ru') if user else 'ru'

    # Send welcome sticker
    try:
        await replace_sticker(message, state, StickerEvent.WELCOME)
    except Exception as e:
        logger.error(f"Failed to send start sticker: {e}")

    await message.answer("Я бот \"Мастера Мерсина\"" +get_text("language_choose", lang), reply_markup=get_language_keyboard(lang))

@router.message(Command("profile"))
@router.callback_query(F.data.in_({"menu_profile", "back_to_profile", "menu_master_profile", "profile"}))
async def cmd_profile(event: Union[Message, CallbackQuery], state: FSMContext, user: dict = None):
    """View user profile - show client or master profile with phone, rating, order stats"""

    if not user:
        return
    lang = user.get('language', 'ru')
    
    # Check if user is a master - show master profile instead
    master = await db.get_master_by_user_id(user['id'])
    if master:
        text = f"🔧 <b>{get_text('menu_master_profile', lang)}:</b>\n\n"
        text += f"<b>{get_text('field_name', lang)}:</b> {master['name']}\n"
        text += f"<b>{get_text('field_phone', lang)}:</b> {master['phone']}\n"
        
        status_key = f"status_{master.get('status', 'pending')}"
        text += f"<b>{get_text('field_status', lang)}:</b> {get_text(status_key, lang)}\n"
        
        # Get localized category and district names from joined tables
        from utils.i18n import get_category_name, get_district_name
        category_names = []
        district_names = []
        
        # Fetch categories from joined table
        master_categories = await db.get_master_categories(master['id'])
        for category in master_categories:
            if category.get('key_field'):
                category_names.append(get_category_name(category['key_field'], lang))
        
        # Fetch districts from joined table
        master_districts = await db.get_master_districts(master['id'])
        for district in master_districts:
            if district.get('key_field'):
                district_names.append(get_district_name(district['key_field'], lang))
        
        text += f"<b>{get_text('field_categories', lang)}:</b> {', '.join(category_names) if category_names else '-'}\n"
        text += f"<b>{get_text('field_districts', lang)}:</b> {', '.join(district_names) if district_names else '-'}\n"
        text += f"<b>{get_text('field_description', lang)}:</b> {master.get('description', '')}\n"

        # Add localized order stats
        stats = await db.get_master_order_stats(master['id'])
        total_orders = stats['total_orders'] or 0
        satisfied_clients = stats['satisfied_clients'] or 0
        
        text += f"\n\n⭐️ {master.get('rating', 0.0):.1f} / 5"
        text += f"\n✅ {total_orders} {get_text('field_orders_count', lang)}"
        
        if master.get('rating', 0.0) >= 4.0 and total_orders > 0:
            percent = round((satisfied_clients / total_orders) * 100)
            text += f"\n{get_text('satisfied_clients_text', lang, percent=percent)}"

        markup = get_master_own_profile_keyboard(master['id'], lang)
        if isinstance(event, Message):
            await event.answer(text, reply_markup=markup)
        else:
            await event.message.edit_text(text, reply_markup=markup)
            await event.answer()
        return
    
    # Show CLIENT profile
    profile = await db.get_or_create_client_profile(user['id'])
    stats = await db.get_client_order_stats(user['id'])
    
    display_name = event.from_user.full_name or event.from_user.username or "Клиент"
    
    text = f"{get_text('client_profile_title', lang)}\n\n"
    text += f"<b>{display_name}</b>\n"
    
    # Phone with verification status
    if profile.get('phone'):
        phone_status = get_text("phone_verified", lang) if profile.get('phone_verified') else get_text("phone_not_verified", lang)
        # Mask phone for privacy
        phone = profile['phone']
        masked_phone = phone[:4] + "..." if len(phone) > 4 else phone
        text += f"📞 {masked_phone} {phone_status}\n\n"
    else:
        text += f"📞 {get_text('phone_not_verified', lang)}\n\n"
    
    # Reliability status
    completed = stats.get('completed', 0)
    cancelled = stats.get('cancelled', 0)
    
    if completed >= 5:
        text += f"{get_text('client_reliable', lang)}\n"
    else:
        text += f"{get_text('client_new', lang)}\n"
    
    text += f"{get_text('client_completed_orders', lang, count=completed)}\n"
    text += f"{get_text('client_cancelled_orders', lang, count=cancelled)}\n"
    
    # Add reputation stats for client profile
    rep_data = await db.get_user_reputation_stats(user['id'])
    c_rep = rep_data.get('as_client', {})
    c_total = c_rep.get('total', 0)
    c_stats = c_rep.get('stats', {})
    
    if c_stats:
        text += f"\n<b>{get_text('reputation_title', lang)} {get_text('as_client_label', lang)}:</b>\n"
        for key, stat in c_stats.items():
            if stat['count'] > 0:
                info = get_text("reputation_based_on", lang, count=stat['count'])
                text += f"{get_text(key, lang)}: {stat['percent']}% {info}\n"
            else:
                info = get_text("reputation_no_info", lang)
                text += f"{get_text(key, lang)} {info}\n"

    markup = get_client_profile_keyboard(lang)
    if isinstance(event, Message):
        await event.answer(text, reply_markup=markup)
    else:
        await event.message.edit_text(text, reply_markup=markup)
        await event.answer()





# Language command
@router.message(Command("lang"))
async def cmd_lang(message: Message, state: FSMContext, user: dict = None):
    """Language selection command"""
    lang = user.get('language', 'ru') if user else 'ru'
    await message.answer(get_text("language_choose", lang), reply_markup=get_language_keyboard(lang))


# TODO: Implement proper language selection and storage
# For now, comment out this handler since language system needs redesign
# @router.callback_query(F.data.in_({"lang_ru", "lang_tr"}))
# async def set_language(callback: CallbackQuery, state: FSMContext):
#     """Set language (RU/TR)."""
#     user_id = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
#     new_lang = callback.data.split("_")[1]
#     # Language storage moved to separate settings table in new schema
#     # await db.update_user_language(user_id, new_lang)
#     await callback.message.edit_text(get_text("start_welcome", new_lang), reply_markup=get_role_keyboard())
#     await state.clear()





@router.callback_query(F.data.in_({"lang_ru", "lang_tr", "lang_en"}))
async def set_language(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Set language (RU/TR) using user service"""
    new_lang = callback.data.split("_")[1]  # Extract 'ru' or 'tr' from callback data
    user_tg_id = callback.from_user.id
    
    # Set language using user service (handles both cache and database)
    success = await set_user_language(user_tg_id, new_lang)
    
    if not success:
        logger.error(f"Failed to set language for user {user_tg_id}")
    user = await globals.db.get_user_by_tg_id(user_tg_id)
    
    # Get updated user for role checking (use injected user)
    # user = await db.get_user_by_tg_id(user_tg_id)
    # is_master = False
    # ... logic already uses 'user' variable which is now the argument
    # We need to ensure 'user' variable refers to the argument, not overwritten
    # But wait, original code assigned 'user = ...'.
    # If I remove the assignment, 'user' refers to the argument.
    
    # Show categories sticker
    try:
        await replace_sticker(callback.message, state, StickerEvent.CATEGORIES)
        await callback.message.delete()
        should_resend = True
    except Exception as e:
        logger.warning(f"Failed to replace sticker in set_language: {e}")
        should_resend = False

    # Always show main menu (role selection is removed)
    if should_resend:
        await callback.message.answer(get_text("main_menu", new_lang, moderator=MODERATOR_USERNAME), reply_markup=await get_main_menu_keyboard(user=user))
    else:
        await callback.message.edit_text(get_text("main_menu", new_lang, moderator=MODERATOR_USERNAME), reply_markup=await get_main_menu_keyboard(user=user))
    
    # Preserve sticker_msg_id when clearing state so replace_sticker can delete old stickers
    await clear_state_preserve_sticker(state)


@router.callback_query(F.data == "back_main_menu")
async def back_main_menu(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    
    try:
        await replace_sticker(callback.message, state, StickerEvent.CATEGORIES)
        await callback.message.delete()
        should_resend = True
    except Exception as e:
        logger.warning(f"Failed to replace sticker in back_main_menu: {e}")
        should_resend = False

    if should_resend:
        await callback.message.answer(get_text("main_menu", lang, moderator=MODERATOR_USERNAME), reply_markup=await get_main_menu_keyboard(user=user))
    else:
        await callback.message.edit_text(get_text("main_menu", lang, moderator=MODERATOR_USERNAME), reply_markup=await get_main_menu_keyboard(user=user))
    
    # Preserve sticker_msg_id when clearing state so replace_sticker can delete old stickers
    await clear_state_preserve_sticker(state)





# ====== FIND MASTER (REQUEST FLOW) ======
@router.callback_query(F.data == "menu_find_master")
async def menu_find_master(callback: CallbackQuery, state: FSMContext, user: dict = None):
    # Check if we need to replace the start sticker
    try:
        await replace_sticker(callback.message, state, StickerEvent.SEARCHING)
        should_resend = False # We don't need to resend the whole message if we are just replacing sticker, 
        # BUT the logic below implies cleaning up old menu.
        # The prompt says: "When state changes: delete previous sticker, send new one, then send text + keyboard".
        # The existing logic tried to delete old sticker msg explicitly. replace_sticker handles that.
        # However, the existing logic also deleted the MENU message to "preserve order".
        # If we want to strictly follow "delete previous sticker, send new one, then send text", 
        # replace_sticker does the sticker part.
        # The menu message handling is separate. 
        # Let's keep the existing logic of deleting the menu message if it was a "back" action that requires a new message stack?
        # Actually, replace_sticker just manages the sticker. 
        # If we want the sticker to be *above* the new text, and we are editing the text, it's fine.
        # If we are sending new text, the sticker should be sent before new text.
        
        # In this handler, we are either editing text or sending new.
        # The original code deleted callback.message.
        # If we use replace_sticker, the sticker is sent as a new message.
        # If we want the menu to be below it, we should verify if we can edit or need to resend.
        # The replace_sticker sends a NEW sticker message.
        # So we probably should let the text be sent as new or edited.
        
        # Let's look at the requirement: "When state changes: ... send new one ... then send text + keyboard".
        # If we edit existing message, the sticker (new message) will be below it? No, sticker is sent to chat.
        # If we edit the existing message, it stays in place. The sticker is appended.
        # To make sticker appear "above", we usually need to send sticker then send text.
        # Or just have the sticker floating at bottom (Telegram default for new messages).
        # "ONLY ONE sticker visible" -> replace_sticker handles this.
        # "then send text + keyboard".
        
        # If we edit the message, the sticker will be passed.
        # Let's trust replace_sticker handles the sticker.
        # We need to decide whether to delete the menu message or edit it.
        # The original code deleted it. Let's stick to editing if possible to avoid jumping, 
        # unless necessary. But replace_sticker sends a NEW message. 
        # If we edit the OLD menu, the NEW sticker will be AFTER the OLD menu.
        # So the order will be [Menu] [Sticker]. We want [Sticker] [Menu].
        # So we MUST delete the old menu and answer with new menu.
        
        # But wait, replace_sticker usage:
        # await replace_sticker(...)
        # BEFORE sending text/keyboard.
        
        # So operation order:
        # 1. replace_sticker() -> sends new sticker msg.
        # 2. answer(text) -> sends new text msg.
        
        # So we should delete the old menu message here if we want strict order.
        # The original code had:
        # await callback.message.delete()
        # should_resend = True
        
        # So:
        # await replace_sticker(...)
        # await callback.message.delete()
        # await callback.message.answer(...)
        
        # But we can't delete callback.message if we want to edit it? 
        # If we delete it, we must answer.
        
    except Exception as e:
        logger.warning(f"Failed to replace sticker: {e}")

    # Explicitly handling the menu re-sending to ensure [Sticker] [Menu] order
    # If we just edit, we get [Menu (edited)] ... [Sticker (new)]. BAD.
    # So we must delete old menu and send new one.
    
    await callback.message.delete() # Delete old menu
    should_resend = True # Force answer() logic below

    lang = user.get('language', 'ru') if user else 'ru'
    # Initialize empty selection
    await state.update_data(selected_category_ids=[])
    
    markup = await get_categories_keyboard_v2(parent_id=None, selected_ids=[], lang=lang)
    text = get_text("find_master_start", lang)

    if should_resend:
        await callback.message.answer(text, reply_markup=markup)
    else:
        # This branch is technically unreachable now with forced delete
        await callback.message.edit_text(text, reply_markup=markup)
        
    await state.set_state(ClientFindMaster.select_service)

@router.callback_query(ClientFindMaster.select_service, F.data.startswith("cat_"))
async def navigate_categories(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    cat_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    markup = await get_categories_keyboard_v2(parent_id=cat_id, selected_ids=selected_ids, lang=lang)
    await callback.message.edit_text(get_text("select_service", lang), reply_markup=markup)

@router.callback_query(ClientFindMaster.select_service, F.data.startswith("sel_"))
async def toggle_category_selection(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    cat_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    if cat_id in selected_ids:
        selected_ids.remove(cat_id)
    else:
        selected_ids.append(cat_id)
        
    await state.update_data(selected_category_ids=selected_ids)
    
    # Refresh current level
    # We need to know the parent_id to refresh. 
    # We can get it from the database or store in state.
    cat = await db.get_category(cat_id)
    parent_id = cat['parent_id'] if cat else None
    
    markup = await get_categories_keyboard_v2(parent_id=parent_id, selected_ids=selected_ids, lang=lang)
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()


@router.callback_query(ClientFindMaster.select_service, F.data == "back_to_groups")
async def back_to_groups(callback: CallbackQuery, state: FSMContext, user: dict = None):
    # Re-using menu_find_master logic for "back to root"
    await menu_find_master(callback, state, user)


@router.callback_query(ClientFindMaster.select_service, F.data == "service_done")
@flags.callback_answer()
async def select_service_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    if not selected_ids:
        await callback.answer(get_text("select_at_least_one_category", lang), show_alert=True)
        return

    # Convert IDs to category info
    category_keys = []
    category_names = []
    
    for cat_id in selected_ids:
        cat = await db.get_category(cat_id)
        if cat:
            cat_key = cat['key_field']
            category_keys.append(cat_key)
            category_names.append(get_category_name(cat_key, lang))
            
    await state.update_data(
        category_keys=category_keys, 
        category_ids=selected_ids,
        category_names=category_names
    )
    
    # Initialize/clear selected districts and proceed
    await state.update_data(selected_districts=[])
    
    await callback.message.edit_text(get_text("select_districts", lang), reply_markup=get_client_districts_keyboard([], lang))
    await state.set_state(ClientFindMaster.select_districts)



@router.callback_query(ClientFindMaster.select_districts, F.data.startswith("cdistrict_"))
@flags.callback_answer()
async def client_select_districts(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    data = await state.get_data()
    selected = data.get("selected_districts", [])

    if callback.data == "cdistrict_done":
        if not selected:
            await callback.answer(get_text("select_at_least_one_district", lang), show_alert=True)
            return
        
        # Convert district indices to district keys and then to IDs
        district_keys = [DISTRICTS[i] for i in selected if 0 <= i < len(DISTRICTS)]
        district_ids = []
        for dist_key in district_keys:
            dist_id = globals.cache_service.get_district_id(dist_key)
            if dist_id:
                district_ids.append(dist_id)
        await state.update_data(district_keys=district_keys, district_ids=district_ids)

        # Search directly with params held in state
        data = await state.get_data()
        category_ids = data.get("category_ids", [])
        
        # Get current user to exclude themselves from results (if they are a master)
        exclude_user_id = user['id'] if user else None
        
        # Search for masters matching this request, excluding the searching user
        masters = await db.search_masters(category_ids, district_ids, exclude_user_id=exclude_user_id)

        if not masters:
            await replace_sticker(callback.message, state, StickerEvent.EMPTY)
            # We must delete old message if we want sticker to be on top?
            # If we utilize replace_sticker (which sends new msg) and then edit_text...
            # The order be: [Menu (edited)] ... [Sticker (new)].
            # We want: [Sticker] [Menu].
            # So again, delete and answer.
            await callback.message.delete()
            await callback.message.answer(get_text("no_masters_found", lang), reply_markup=get_add_master_keyboard(lang))
            await clear_state_preserve_sticker(state)
            return

        # Store results and show first page
        # Sticker for success/found?
        # "master_found": "..."
        await replace_sticker(callback.message, state, StickerEvent.MASTER_FOUND)
        
        # We need to ensure order [Sticker] [Results].
        # So delete old and answer new.
        await callback.message.delete()
        
        await state.update_data(masters_list=masters, current_page=0)
        await state.set_state(ClientFindMaster.viewing_results)
        await send_masters_page(callback.message, state, 0, user=user)
        return

    try:
        idx = int(callback.data.split("_")[1])
    except Exception:
        await callback.answer(get_text("error", lang), show_alert=True)
        return

    if idx in selected:
        selected.remove(idx)
    else:
        selected.append(idx)

    await state.update_data(selected_districts=selected)
    await callback.message.edit_reply_markup(reply_markup=get_client_districts_keyboard(selected, lang))


@router.callback_query(ClientFindMaster.select_districts, F.data == "back_to_services")
async def back_to_services(callback: CallbackQuery, state: FSMContext, user: dict = None):
    # This might be tricky because we don't know the exact level we came from.
    # We'll just go back to root for now or store last parent_id.
    await menu_find_master(callback, state, user)


async def send_masters_page(message: Message, state: FSMContext, page: int = 0, user: dict = None):
    """Helper to send a specific page of master results"""
    data = await state.get_data()
    all_masters = data.get("masters_list", [])
    lang = user.get('language', 'ru') if user else 'ru'
    
    # Calculate paging
    items_per_page = 10
    total_pages = (len(all_masters) + items_per_page - 1) // items_per_page
    if total_pages < 1: total_pages = 1
    
    # Bound check
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_masters = all_masters[start_idx:end_idx]

    text = get_text("search_results_header", lang, count=len(all_masters))
    
    # send_masters_page is called after we already handled sticker and deleted previous message in the caller.
    # So we should just Answer.
    # BUT send_masters_page is also called by Next/Prev buttons which use edit_text.
    # We shouldn't resend Sticker on pagination.
    
    # Check if we are editing (message exists and wasn't deleted)
    # The caller for "search" deleted the message passed as 'callback.message'.
    # But wait, 'callback.message' is a Message object. deleting it on Telegram doesn't invalidate the object.
    # But we can't edit a deleted message.
    
    # Logic in caller (client_select_districts):
    # await callback.message.delete()
    # await send_masters_page(callback.message, ...)
    # So here message is likely the deleted message.
    
    try:
        await message.edit_text(
            text, 
            reply_markup=get_masters_keyboard(page_masters, page, total_pages, lang)
        )
    except Exception:
        # If edit fails (e.g. message deleted), send new
        await message.answer(
            text, 
            reply_markup=get_masters_keyboard(page_masters, page, total_pages, lang)
        )
    await state.update_data(current_page=page)


@router.callback_query(ClientFindMaster.viewing_results, F.data == "masters_page_prev")
async def masters_page_prev(callback: CallbackQuery, state: FSMContext, user: dict = None):
    data = await state.get_data()
    current_page = data.get("current_page", 0)
    await send_masters_page(callback.message, state, current_page - 1, user=user)
    await callback.answer()


@router.callback_query(ClientFindMaster.viewing_results, F.data == "masters_page_next")
async def masters_page_next(callback: CallbackQuery, state: FSMContext, user: dict = None):
    data = await state.get_data()
    current_page = data.get("current_page", 0)
    await send_masters_page(callback.message, state, current_page + 1, user=user)
    await callback.answer()


@router.callback_query(ClientFindMaster.viewing_results, F.data == "noop")
async def masters_page_noop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()



# ====== MY ORDERS ======
@router.callback_query(F.data == "menu_my_orders")
async def menu_my_orders(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show client's orders - active orders first, then completed history"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    # Fetch active orders
    active_orders = await db.get_active_orders(user['id'])
    completed_count = await db.get_completed_orders_count(user['id'])
    
    # No orders at all
    if not active_orders and completed_count == 0:
        await callback.message.edit_text(
            get_text("no_orders", lang), 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")]
            ])
        )
        return
    
    # Case 1: Has active orders - show them prominently
    if active_orders:
        text = get_text("orders_list_title", lang) + "\n\n"
        
        for order in active_orders:
            # Build active order display
            order_id = order['id']
            master_name = order.get('master_name', '-')
            
            # Get category name
            cat_key = order.get('category_key')
            if cat_key:
                cat_name = get_category_name(cat_key, lang)
            else:
                cat_name = "-"
            
            # Add active order notice
            text += get_text("active_order_notice", lang, id=order_id) + "\n"
            text += get_text("active_order_master", lang, name=master_name) + "\n"
            text += get_text("active_order_categories", lang, categories=cat_name) + "\n"
            text += "\n" + get_text("active_order_complete_prompt", lang) + "\n"
            text += "──────────────────\n"
        
        # Build keyboard with completion buttons
        has_history = completed_count > 0
        keyboard = get_orders_menu_keyboard(active_orders, has_history, lang)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        return
    
    # Case 2: No active orders - show completed orders with pagination
    await show_completed_orders_page(callback, user, 0)


async def show_completed_orders_page(callback: CallbackQuery, user: dict, page: int):
    """Helper to display paginated completed orders"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    completed_orders = await db.get_completed_orders(user['id'], limit=5, offset=page*5)
    total_count = await db.get_completed_orders_count(user['id'])
    total_pages = (total_count + 4) // 5  # Round up
    
    if not completed_orders:
        await callback.message.edit_text(
            get_text("no_completed_orders", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")]
            ])
        )
        return
    
    text = get_text("orders_history_title", lang) + "\n\n"
    
    for order in completed_orders:
        dt = order['created_at']
        if isinstance(dt, str):
            date_str = dt.split("T")[0]
            time_str = dt.split("T")[1].split(".")[0]
        else:
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
        
        # Resolve category name
        cat_key = order.get('category_key')
        if cat_key:
            cat_name = get_category_name(cat_key, lang)
        else:
            cat_name = order.get('category_name') or '-'
        
        rating = order.get('rating') or '-'
        item_text = get_text("order_item_completed", lang,
            date=date_str, time_str=time_str, category=cat_name, master_name=order['master_name'], rating=rating)
        
        text += f"{item_text}\n──────────────────\n"
    
    # Determine back button destination:
    # If there are active orders, "Back" should go to the "active orders" view (menu_my_orders).
    # If there are NO active orders, "Back" should go to the Main Menu (back_main_menu).
    active_count = await db.get_active_orders_count(user['id'])
    back_cb = "menu_my_orders" if active_count > 0 else "back_main_menu"
    
    keyboard = get_orders_history_keyboard(page, total_pages, lang, back_callback=back_cb)
    await callback.message.edit_text(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("orders_history_page_"))
async def orders_history_page(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Handle pagination for order history"""
    page = int(callback.data.split("_")[-1])
    await show_completed_orders_page(callback, user, page)


# ====== CONCIERGE FLOW ======
@router.callback_query(F.data == "menu_concierge")
@flags.callback_answer()
async def menu_concierge(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    # Initialize empty list for selected topics
    await state.update_data(selected_topics=[])
    await callback.message.edit_text(get_text("concierge_intro", lang) + "\n\n" + get_text("concierge_choose_topic", lang), reply_markup=get_concierge_topics_keyboard([], lang))
    await state.set_state(ClientConcierge.select_topic)


@router.callback_query(ClientConcierge.select_topic, F.data.startswith("concierge_toggle_"))
@flags.callback_answer()
async def toggle_concierge_topic(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    topic = callback.data.replace("concierge_toggle_", "")
    
    data = await state.get_data()
    selected = data.get("selected_topics", [])
    
    if topic in selected:
        selected.remove(topic)
    else:
        selected.append(topic)
    
    await state.update_data(selected_topics=selected)
    await callback.message.edit_reply_markup(reply_markup=get_concierge_topics_keyboard(selected, lang))


@router.callback_query(ClientConcierge.select_topic, F.data == "concierge_done")
async def select_concierge_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    selected = data.get("selected_topics", [])
    
    if not selected:
        await callback.answer(get_text("select_at_least_one_category", lang), show_alert=True)
        return
        
    await callback.message.delete()
    await callback.message.answer(get_text("concierge_phone", lang), reply_markup=get_share_phone_keyboard(lang))
    await state.set_state(ClientConcierge.phone)


@router.message(ClientConcierge.phone)
async def concierge_phone(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    if message.contact:
        phone = normalize_phone(message.contact.phone_number)
    else:
        raw_phone = (message.text or "").strip()
        if not is_valid_phone(raw_phone):
            await message.answer(get_text("invalid_phone", lang))
            return
        phone = normalize_phone(raw_phone)

    await state.update_data(phone=phone)
    await message.answer(get_text("concierge_enter_name", lang), reply_markup=get_remove_keyboard())
    await state.set_state(ClientConcierge.name)


@router.message(ClientConcierge.name)
async def concierge_name(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    name = (message.text or "").strip()

    if not name:
        await message.answer(get_text("concierge_name_required", lang))
        return

    state_data = await state.get_data()
    selected_topics = state_data.get("selected_topics", [])
    phone = state_data.get("phone", "")

    # Resolve topic names (use Russian for DB/Admin by default)
    admin_lang = 'ru'
    resolved_topics = [get_text(t, admin_lang) for t in selected_topics]
    topics_display = ", ".join(resolved_topics)

    try:
        # Save to database
        await db.create_concierge_request(user['id'], topics_display, phone, name)
    except Exception:
        logger.exception("Failed to create concierge request")

    # Notify admins (best-effort)
    try:

        
        # Determine filling language
        filling_language = "Русский" if lang == "ru" else "Турецкий"
        
        for admin_tg_id in ADMIN_IDS:
            await bot.send_message(
                admin_tg_id,
                get_text(
                    "admin_concierge_new",
                    admin_lang,
                    service=topics_display,
                    phone=phone,
                    name=name,
                    lang_tag=filling_language
                ),
            )
    except Exception:
        logger.exception("Failed to notify admins about concierge request")

    await replace_sticker(message, state, StickerEvent.CATEGORIES)
    await message.answer(get_text("concierge_submitted", lang), reply_markup=await get_main_menu_keyboard(user=user))
    await clear_state_preserve_sticker(state)

# ====== DISTRICT SELECTION ======
@router.callback_query(ClientSearch.select_district, F.data.startswith("district_"))
@flags.callback_answer()
async def select_district(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Client selects district"""
    lang = user.get('language', 'ru') if user else 'ru'
    district_idx = int(callback.data.split("_")[1])
    
    await state.update_data(district=DISTRICTS[district_idx])
    
    text = get_text("select_category", lang)
    await callback.message.edit_text(text, reply_markup=get_categories_keyboard())
    await state.set_state(ClientSearch.select_category)

# ====== MASTER PROFILE ======
@router.callback_query(F.data.startswith("master_profile_"))
async def view_master_profile(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """View master profile"""
    lang = user.get('language', 'ru') if user else 'ru'
    master_id = int(callback.data.split("_")[2])
    
    master = await db.get_master(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
    
    # Localize districts and categories
    districts = [get_district_name(d, lang) for d in master.get('districts', [])]
    categories = [get_category_name(c, lang) for c in master.get('categories', [])]
    
    status = master.get('status', 'pending')
    status_symbol = "👻"
    if status == 'active_premium':
        status_symbol = "🔧💎"
    elif status == 'active_free':
        status_symbol = "🔧"
    
    rating_val = master.get('rating', 0.0)
    rating_display = f" ⭐️{rating_val:.1f}" if rating_val and rating_val > 0 else ""

    text = get_text("master_card", lang, 
        status_symbol=status_symbol,
        name=master['name'],
        rating_display=rating_display,
        districts=", ".join(districts),
        categories=", ".join(categories),
        description=master['description']
    )

    # Add localized order stats
    stats = await db.get_master_order_stats(master_id)
    total_orders = stats['total_orders'] or 0
    satisfied_clients = stats['satisfied_clients'] or 0
    
    text += f"\n\n⭐️ {rating_val:.1f} / 5"
    text += f"\n✅ {total_orders} {get_text('field_orders_count', lang)}"
    
    if rating_val > 4.0 and total_orders > 0:
        percent = round((satisfied_clients / total_orders) * 100)
        text += f"\n{get_text('satisfied_clients_text', lang, percent=percent)}"
    
    await callback.message.edit_text(text, reply_markup=get_master_profile_keyboard(master_id, lang))


@router.callback_query(F.data.startswith("master_reputation_"))
async def view_master_reputation(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """View master reputation stats (checklist results)"""
    lang = user.get('language', 'ru') if user else 'ru'
    master_id = int(callback.data.split("_")[2])
    
    master = await db.get_master(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
        
    rep_data = await db.get_user_reputation_stats(master['user_id'])
    m_rep = rep_data.get('as_master', {})
    m_stats = m_rep.get('stats', {})
    
    text = f"<b>{get_text('reputation_title', lang)}: {master['name']}</b>\n\n"
    
    if m_stats:
        for key, stat in m_stats.items():
            if stat['count'] > 0:
                info = get_text("reputation_based_on", lang, count=stat['count'])
                text += f"{get_text(key, lang)}: {stat['percent']}% {info}\n"
            else:
                info = get_text("reputation_no_info", lang)
                text += f"{get_text(key, lang)} {info}\n"
    else:
        text += get_text("reputation_no_info", lang)

    # If the viewer is the master themselves, back to menu_profile
    back_callback = "menu_profile" if master['user_id'] == user['id'] else f"master_profile_{master_id}"

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=back_callback)]
    ])
    
    await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data == "back_to_results")
async def back_to_results(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Back to master list from profile"""
    data = await state.get_data()
    masters = data.get("masters_list")
    if not masters:
        # Fallback to menu if no results in state
        return await back_main_menu(callback, state, user)
        
    current_page = data.get("current_page", 0)
    await send_masters_page(callback.message, state, current_page, user=user)


@router.callback_query(F.data.startswith("master_contact_"))
async def contact_master(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show master contact"""
    master_id = int(callback.data.split("_")[2])
    master = await db.get_master(master_id)
    
    phone = master['phone'] or "N/A"
    # Language-aware header and buttons
    lang = user.get('language', 'ru') if user else 'ru'
    header = get_text("master_contact", lang, name=master['name'])
    start_btn = get_text("order_start", lang)
    back_btn = get_text("btn_back", lang)
    text = f"{header}\n\n{phone}\n\n" + get_text("start_order_instructions", lang, start_button=start_btn)
    
    await replace_sticker(callback.message, state, StickerEvent.CONTACT)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=start_btn, callback_data=f"order_start_{master_id}")],
            [InlineKeyboardButton(text=back_btn, callback_data=f"master_profile_{master_id}")]
        ])
    )

@router.callback_query(F.data.startswith("master_reviews_"))
async def view_master_reviews(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """View master reviews"""
    master_id = int(callback.data.split("_")[2])
    reviews = await db.get_master_reviews(master_id)
    lang = user.get('language', 'ru') if user else 'ru'
    
    # Localize headers and empty state using i18n
    header_text = get_text("master_reviews_header", lang)
    no_reviews_text = get_text("reviews_no", lang)
    
    if not reviews:
        text = f"⭐ <b>{header_text}:</b> {no_reviews_text}"
    else:
        text = f"⭐ <b>{header_text}:</b>\n\n"
        for review in reviews[:5]:  # Show last 5
            text += f"{'⭐' * review['rating']} {review['price']}₺\n{review['review_text']}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=f"master_profile_{master_id}")]
        ])
    )

# ====== REPORT MASTER ======
@router.callback_query(F.data.startswith("master_report_"))
async def report_master_prompt(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Prompt to report master"""
    lang = user.get('language', 'ru') if user else 'ru'
    master_id = int(callback.data.split("_")[2])
    
    await state.update_data(report_master_id=master_id)
    
    text = get_text("report_text_prompt", lang)
    # Add back button to profile
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=f"master_profile_{master_id}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb)
    await state.set_state(ClientReport.waiting_text)

@router.message(ClientReport.waiting_text)
async def report_master_submit(message: Message, state: FSMContext, user: dict = None):
    """Submit report"""
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    master_id = data.get("report_master_id")
    text = (message.text or "").strip()
    
    if not text:
        await message.answer("Пожалуйста, опишите проблему текстом.", reply_markup=get_remove_keyboard())
        return

    # Save to DB
    if master_id:
        await db.create_complaint(user['id'], master_id, text)
        
    await message.answer(
        get_text("report_submitted", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_menu", lang), callback_data="back_main_menu")]
        ])
    )
    await state.clear()


# ====== ORDER START ======
@router.callback_query(F.data.startswith("order_start_"))
async def start_order(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Start order with master - requires verified phone"""
    lang = user.get('language', 'ru') if user else 'ru'
    master_id = int(callback.data.split("_")[2])
    
    master = await db.get_master(master_id)
    if not master:
        await callback.answer("❌ Мастер не найден", show_alert=True)
        return
    
    state_data = await state.get_data()
    # Try to get new multi-select categories, fall back to legacy 'category'
    category_ids = state_data.get("category_ids", [])
    category_id = category_ids[0] if category_ids else None
    
    # Get category name for notification
    category_name = "Услуга"
    if category_id:
        # We might not have easy access to cat name here without querying DB, 
        # but we might have category_names in state
        c_names = state_data.get("category_names", [])
        if c_names:
            category_name = c_names[0]
            if len(c_names) > 1:
                category_name += " и др."
    
    # Check if client has verified phone
    profile = await db.get_client_profile(user['id'])
    
    if not profile or not profile.get('phone_verified'):
        # Need to verify phone first
        await state.update_data(
            pending_order_master_id=master_id,
            category_ids=category_ids,
            category_names=state_data.get("category_names", [])
        )
        
        await callback.message.answer(
            get_text("share_phone_prompt", lang),
            reply_markup=get_share_phone_keyboard(lang)
        )
        await state.set_state(ClientPhoneVerification.waiting_contact)
        await callback.answer()
        return
    
    # Create order
    order_id = await db.create_order(user['id'], master_id, category_id)
    
    text = get_text("order_started", lang,
        master_name=master['name'],
        phone=master['phone']
    )

    await replace_sticker(callback.message, state, StickerEvent.ORDER_STARTED)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(text, reply_markup=get_order_completion_keyboard(order_id, lang))
    await state.update_data(order_id=order_id)

    # Notify master
    if master.get('user_id') != -1:
        master_user = await db.get_user(master['user_id'])
        if master_user:
            master_lang = master_user.get('language', 'ru')
            
            # Use username if available, otherwise use phone from profile
            client_username = user.get('username')
            if client_username:
                client_info = f"@{client_username}"
            else:
                client_info = profile.get('phone', 'N/A') if profile else 'N/A'
            
            notify_text = get_text(
                "master_notify_new_order",
                master_lang,
                category=category_name,
                client_info=client_info
            )
            try:
                await bot.send_message(master_user['telegram_id'], notify_text)
            except Exception as e:
                logger.error(f"Could not notify master {master_id}: {e}")


# ====== ORDER COMPLETION & REVIEW ======
@router.callback_query(F.data.startswith("order_complete_"))
async def complete_order(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Mark order as completed and start review"""
    lang = user.get('language', 'ru') if user else 'ru'
    order_id = int(callback.data.split("_")[2])
    
    #await db.complete_order(order_id)
    
    text = get_text("review_what_done", lang)
    await callback.message.edit_text(text)
    await state.set_state(ClientReview.what_done)
    await state.update_data(order_id=order_id)

@router.message(ClientReview.what_done)
async def review_what_done(message: Message, state: FSMContext, user: dict = None):
    """Client describes what was done"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    await state.update_data(what_done=message.text)
    
    text = get_text("review_price", lang)
    await message.answer(text)
    await state.set_state(ClientReview.price)

@router.message(ClientReview.price)
async def review_price(message: Message, state: FSMContext, user: dict = None):
    """Client specifies price"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("❌ Введите число (в ₺)")
        return
    
    await state.update_data(price=price)
    data = await state.get_data()
    order_id = data.get("order_id", 0)
    
    # NEW: Fetch criteria from DB
    criteria = await db.get_criteria(role_client=True)
    await state.update_data(criteria=criteria, selected_criteria_ids=[])
    
    await message.answer(
        get_text("master_feedback_question", lang),
        reply_markup=get_client_master_feedback_checklist_keyboard(order_id, criteria=criteria, selected_ids=[], lang=lang)
    )
    await state.set_state(ClientReview.feedback)


@router.callback_query(ClientReview.feedback, F.data.startswith("mfdbk_toggle_"))
@flags.callback_answer()
async def toggle_master_feedback(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Toggle a selection in the master feedback checklist with mutual exclusion"""
    lang = user.get('language', 'ru') if user else 'ru'
    try:
        criterion_id = int(callback.data.replace("mfdbk_toggle_", ""))
    except ValueError:
        await callback.answer()
        return
    
    data = await state.get_data()
    selected_ids = data.get("selected_criteria_ids", [])
    criteria = data.get("criteria", [])
    order_id = data.get("order_id")
    
    # Find the criterion and its group
    target_criterion = next((c for c in criteria if c['id'] == criterion_id), None)
    if not target_criterion:
        await callback.answer()
        return
        
    group_key = target_criterion.get('group_key')
    
    if criterion_id in selected_ids:
        selected_ids.remove(criterion_id)
    else:
        # Mutual exclusion: remove other criteria from the same group
        if group_key:
            ids_in_same_group = [c['id'] for c in criteria if c.get('group_key') == group_key]
            selected_ids = [sid for sid in selected_ids if sid not in ids_in_same_group]
        
        selected_ids.append(criterion_id)
        
    await state.update_data(selected_criteria_ids=selected_ids)
    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=get_client_master_feedback_checklist_keyboard(order_id, criteria=criteria, selected_ids=selected_ids, lang=lang)
    )

@router.callback_query(ClientReview.feedback, F.data.startswith("mfdbk_done_"))
@flags.callback_answer()
async def master_feedback_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """After checklist, prompt for text comment"""
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    order_id = data.get("order_id", 0)
    
    await callback.message.edit_text(
        get_text("review_comment", lang),
        reply_markup=get_skip_feedback_keyboard(order_id, lang)
    )
    await state.set_state(ClientReview.comment)


@router.callback_query(ClientReview.comment, F.data.startswith("skip_client_feedback_"))
async def skip_review_comment(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Client skips optional text comment"""
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    order_id = data.get("order_id", 0)
    
    await state.update_data(comment="")
    
    await callback.message.edit_text(
        get_text("review_rating", lang),
        reply_markup=get_rating_keyboard(order_id)
    )
    await state.set_state(ClientReview.rating)


@router.message(ClientReview.comment)
async def review_comment(message: Message, state: FSMContext, user: dict = None):
    """Client leaves optional comment"""
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    order_id = data.get("order_id", 0)
    
    await state.update_data(comment=(message.text or "").strip())
    
    await message.answer(
        get_text("review_rating", lang),
        reply_markup=get_rating_keyboard(order_id)
    )
    await state.set_state(ClientReview.rating)


@router.callback_query(ClientReview.rating, F.data.startswith("rating_"))
async def review_rating(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Final step: Client rates master and saves everything"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    rating = int(callback.data.split("_")[2])
    
    state_data = await state.get_data()
    order_id = state_data['order_id']
    price = state_data['price']
    what_done = state_data['what_done']
    selected_criteria_ids = state_data.get("selected_criteria_ids", [])
    comment = state_data.get("comment", "")
    
    # Complete order in DB
    await db.complete_order(
        order_id=order_id,
        rating=rating,
        price=price,
        review=what_done + "\n" + comment
    )
    
    # Save reputation votes
    await db.save_votes(from_client=True, order_id=order_id, criterion_ids=selected_criteria_ids)
    
    # Update master rating
    order = await db.get_order(order_id)
    await db.update_master_rating(order['master_id'])
    
    # Update client order stats
    await db.update_client_order_stats(user['id'])

    await replace_sticker(callback.message, state, StickerEvent.FEEDBACK)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(
        get_text("review_submitted", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_menu", lang), callback_data="back_main_menu")]
        ])
    )

    # Notify admins on low rating (best-effort)
    # try:
    #     if rating <= 3:
    #         master = await db.get_master(order['master_id'])
    #         master_name = master.get('name') if master else "-"
    #         for admin_tg_id in ADMIN_IDS:
    #             admin_lang = 'ru'
    #             await bot.send_message(
    #                 admin_tg_id,
    #                 get_text(
    #                     "admin_review_issue",
    #                     admin_lang,
    #                     master_name=master_name,
    #                     rating=rating,
    #                     comment=comment or "-",
    #                 ),
    #             )
    # except Exception:
    #     logger.exception("Failed to notify admins about low rating")

    # Notify master about order completion and ask to rate client
    try:
        master = await db.get_master(order['master_id'])
        if master and master.get('user_id') != -1:
            master_user = await db.get_user(master['user_id'])
            if master_user:
                master_lang = master_user.get('language', 'ru')
                
                # Use username if available, otherwise use phone from profile
                client_username = user.get('username')
                if client_username:
                    client_info = f"@{client_username}"
                else:
                    client_profile = await db.get_client_profile(user['id'])
                    client_info = client_profile.get('phone', 'N/A') if client_profile else 'N/A'

                # Create rate client keyboard with master's language
                rate_client_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=get_text("master_rate_client", master_lang), callback_data=f"rate_client_{order_id}")]
                ])
                
                notify_text = get_text(
                    "master_notify_order_completed",
                    master_lang,
                    order_id=order_id,
                    client_info=client_info,
                    price=price,
                    rating=rating
                )
                
                await bot.send_message(master_user['telegram_id'], notify_text, reply_markup=rate_client_kb)
    except Exception:
        logger.exception("Failed to notify master about order completion")
    
    await clear_state_preserve_sticker(state)


@router.callback_query(F.data == "order_cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Cancel order"""
    await callback.message.edit_text("❌ Заказ отменён")
    await clear_state_preserve_sticker(state)

@router.callback_query(F.data == "back_to_search")
@flags.callback_answer()
async def back_to_search(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Back to master search"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    text = get_text("start_client", lang)
    await callback.message.edit_text(text, reply_markup=get_districts_keyboard())
    await state.set_state(ClientSearch.select_district)

# ====== ADD MASTER ======
@router.callback_query(F.data == "add_master")
async def add_master_prompt(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Prompt to add new master"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    text = get_text("add_master_form", lang)
    await callback.message.edit_text(text)
    await state.set_state(ClientAddMaster.master_name)

@router.message(ClientAddMaster.master_name)
async def add_master_name(message: Message, state: FSMContext, user: dict = None):
    """Master name input"""
    await state.update_data(master_name=message.text)
    
    lang = user.get('language', 'ru') if user else 'ru'
    text = get_text("master_phone", lang)
    await message.answer(text)
    await state.set_state(ClientAddMaster.master_phone)

@router.message(ClientAddMaster.master_phone)
async def add_master_phone(message: Message, state: FSMContext, user: dict = None):
    """Master phone input"""
    raw_phone = (message.text or "").strip()
    lang = user.get('language', 'ru') if user else 'ru'
    
    if not is_valid_phone(raw_phone):
        await message.answer(get_text("invalid_phone", lang))
        return

    phone = normalize_phone(raw_phone)
    # Check for existing phone
    existing_master = await db.get_master_by_phone(phone)
    if existing_master:
        if existing_master.get('user_id') == -1:
            print(existing_master.get('user_id'))
            # Handle unlinked master profile
            # Point to admins using tg://user?id=... format as we only have IDs in config
            admin_links = MODERATOR_USERNAME #", ".join([f'<a href="tg://user?id={aid}">👨‍💼moder{aid}</a>' for aid in ADMIN_IDS])
            text = get_text("claim_master_prompt", lang, admin_links=admin_links)
            
            await state.update_data(claim_master_id=existing_master['id'], claim_master_phone=phone)
            await message.answer(text, reply_markup=get_share_phone_keyboard(lang), parse_mode="HTML")
            await state.set_state(ClientAddMaster.claiming_master)
            return
        print('race')
        await message.answer(get_text("phone_already_registered", lang))
        return

    await state.update_data(master_phone=phone)
    
    text = get_text("master_districts", lang)
    await message.answer(text, reply_markup=get_master_districts_keyboard())
    await state.set_state(ClientAddMaster.master_districts)

@router.callback_query(ClientAddMaster.master_districts, F.data.startswith("mdistrict_"))
@flags.callback_answer()
async def add_master_districts(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Master districts multi-select"""
    state_data = await state.get_data()
    selected = state_data.get("selected_districts", [])
    lang = user.get('language', 'ru') if user else 'ru'
        
    if callback.data == "mdistrict_done":
        # Move to categories
        text = get_text("master_categories", lang)
        # Use v2 keyboard
        markup = await get_categories_keyboard_v2(parent_id=None, selected_ids=[], lang=lang)
        await callback.message.edit_text(text, reply_markup=markup)
        await state.set_state(ClientAddMaster.master_categories)
    else:
        idx = int(callback.data.split("_")[1])
        if idx in selected:
            selected.remove(idx)
        else:
            selected.append(idx)
        
        await state.update_data(selected_districts=selected)
        await callback.message.edit_reply_markup(reply_markup=get_master_districts_keyboard(selected, lang))

@router.callback_query(ClientAddMaster.master_categories, F.data.startswith("cat_"))
async def add_master_navigate_categories(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    cat_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    markup = await get_categories_keyboard_v2(parent_id=cat_id, selected_ids=selected_ids, lang=lang)
    await callback.message.edit_text(get_text("master_categories", lang), reply_markup=markup)

@router.callback_query(ClientAddMaster.master_categories, F.data.startswith("sel_"))
async def add_master_toggle_category_selection(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    cat_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    if cat_id in selected_ids:
        selected_ids.remove(cat_id)
    else:
        selected_ids.append(cat_id)
        
    await state.update_data(selected_category_ids=selected_ids)
    
    cat = await db.get_category(cat_id)
    parent_id = cat['parent_id'] if cat else None
    
    markup = await get_categories_keyboard_v2(parent_id=parent_id, selected_ids=selected_ids, lang=lang)
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()

@router.callback_query(ClientAddMaster.master_categories, F.data == "service_done")
async def add_master_categories_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])

    if not selected_ids:
        await callback.answer(get_text("select_at_least_one_category", lang), show_alert=True)
        return

    # Store IDs for confirmation
    await state.update_data(selected_categories=selected_ids)

    text = get_text("master_description", lang)
    await callback.message.edit_text(text)
    await state.set_state(ClientAddMaster.confirmation)

@router.message(ClientAddMaster.confirmation)
async def add_master_confirm(message: Message, state: FSMContext, user: dict = None):
    """Save new master to DB"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    data = await state.get_data()
    
    # Convert district indices to district keys and then to IDs
    selected_district_indices = data.get("selected_districts", [])
    district_keys = [DISTRICTS[i] for i in selected_district_indices if 0 <= i < len(DISTRICTS)]
    
    # Resolve category names and IDs
    selected_category_ids = data.get("selected_categories", [])
    
    category_ids = []
    category_names = []
    for cat_id in selected_category_ids:
        cat = await db.get_category(cat_id)
        if cat:
            category_ids.append(cat['id'])
            category_names.append(get_category_name(cat['key_field'], lang))
    
    district_ids = [DISTRICTS[i] for i in selected_district_indices if 0 <= i < len(DISTRICTS)]
    # (Simplified for now - district logic remains legacy as districts didn't change structure)
    # Wait, the code above had district_ids as actual IDs. Let's fix it.
    
    district_db_ids = []
    for dist_key in district_ids:
        dist = await db.get_district_by_key(dist_key)
        if dist:
            district_db_ids.append(dist['id'])
    
    district_ids = district_db_ids
    
    description = (message.text or "").strip()
    if not description:
        await message.answer(get_text("master_description", lang))
        return

    limit = 100
    if len(description) > limit:
        await message.answer(get_text("description_too_long", lang, limit=limit, length=len(description)))
        return
    
    # Create unverified master
    try:
        await db.create_master(
            user_id=-1,
            name=data['master_name'],
            phone=data['master_phone'],
            description=description,
            categories=category_ids,
            districts=district_ids,
            source="user",
            status="pending"
        )
        
        text = get_text("master_added", lang)
        await replace_sticker(message, state, StickerEvent.CATEGORIES)
        await message.answer(text, reply_markup=await get_main_menu_keyboard(user=user))
        await clear_state_preserve_sticker(state)
        
    except Exception as e:
        logger.exception(f"Failed to add master: {e}")
        error_text = get_text("error", lang)
        # If it's a conflict or specific DB error, we could be more specific
        await message.answer(error_text)
        # Keep state for retry or let user restart


@router.message(ClientAddMaster.claiming_master, F.contact)
async def claim_master_contact(message: Message, state: FSMContext, user: dict = None):
    """Handle shared contact for claiming an unlinked master profile"""
    lang = user.get('language', 'ru') if user else 'ru'
    shared_phone = normalize_phone(message.contact.phone_number)
    
    data = await state.get_data()
    master_phone = data.get("claim_master_phone")
    master_id = data.get("claim_master_id")
    
    if shared_phone == master_phone:
        # Link master to user
        await db.link_master_to_user(master_id, user['id'])
        # Set user as master
        await db.set_user_master(user['id'], True)
        
        # Reload user to ensure cache reflects is_master=True
        updated_user = await db.get_user(user['id'])
        
        await replace_sticker(message, state, StickerEvent.CATEGORIES)
        await message.answer(get_text("master_claimed", lang), reply_markup=await get_main_menu_keyboard(user=updated_user))
        await clear_state_preserve_sticker(state)
    else:
        await message.answer(get_text("phone_mismatch", lang))


@router.message(ClientAddMaster.claiming_master)
async def claim_master_text(message: Message, state: FSMContext, user: dict = None):
    """Remind to share contact during claiming process"""
    lang = user.get('language', 'ru') if user else 'ru'
    admin_links = ", ".join([f'<a href="tg://user?id={aid}">👨‍💼moder{aid}</a>' for aid in ADMIN_IDS])
    await message.answer(
        get_text("claim_master_prompt", lang, admin_links=admin_links),
        reply_markup=get_share_phone_keyboard(lang),
        parse_mode="HTML"
    )


# ====== CLIENT PROFILE BUTTON HANDLERS ======
@router.callback_query(F.data == "client_history")
async def client_history(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show client order history - same as menu_my_orders"""
    await menu_my_orders(callback, state, user=user)


@router.callback_query(F.data == "client_change_phone")
async def client_change_phone(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Start phone change flow"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    await callback.message.answer(
        get_text("phone_change_prompt", lang),
        reply_markup=get_share_phone_keyboard(lang)
    )
    await state.set_state(ClientChangePhone.waiting_contact)
    await callback.answer()


@router.callback_query(F.data == "client_my_reviews")
async def client_my_reviews(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Show reviews this client has given to masters"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    reviews = await db.get_client_reviews_for_masters(user['id'])
    
    if not reviews:
        text = get_text("no_reviews_yet", lang)
    else:
        text = get_text("my_reviews_title", lang) + "\n\n"
        for review in reviews[:10]:
            dt = review.get('completed_at')
            if isinstance(dt, str):
                date_str = dt.split("T")[0]
            elif dt:
                date_str = dt.strftime("%Y-%m-%d")
            else:
                date_str = ""
            
            cat_name = get_category_name(review.get('category_key', ''), lang) if review.get('category_key') else '-'
            
            text += get_text("review_item", lang, 
                master_name=review.get('master_name', '-'),
                rating=review.get('rating', '-'),
                category=cat_name,
                date=date_str
            ) + "\n\n"
    
    await callback.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="menu_profile")]
        ])
    )


# ====== PHONE VERIFICATION HANDLERS ======
@router.message(ClientPhoneVerification.waiting_contact, F.contact)
async def phone_verification_contact(message: Message, state: FSMContext, user: dict = None):
    """Handle shared contact for phone verification"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    phone = normalize_phone(message.contact.phone_number)
    
    # Create or update client profile with verified phone
    profile = await db.get_client_profile(user['id'])
    if profile:
        await db.update_client_phone(user['id'], phone, phone_verified=True)
    else:
        await db.create_client_profile(user['id'], phone=phone, phone_verified=True)
    
    await message.answer(
        get_text("phone_confirmed", lang), 
        reply_markup=get_remove_keyboard()
    )
    
    # Check if we were in the middle of starting an order
    data = await state.get_data()
    pending_master_id = data.get("pending_order_master_id")
    
    if pending_master_id:
        # Continue with order creation
        master = await db.get_master(pending_master_id)
        if master:
            category_ids = data.get("category_ids", [])
            category_id = category_ids[0] if category_ids else None
            
            order_id = await db.create_order(user['id'], pending_master_id, category_id)
            
            text = get_text("order_started", lang,
                master_name=master['name'],
                phone=master['phone']
            )
            
            await message.answer(text, reply_markup=get_order_completion_keyboard(order_id,lang))
            
            # Notify master
            if master.get('user_id') != -1:
                master_user = await db.get_user(master['user_id'])
                if master_user:
                    master_lang = master_user.get('language', 'ru')
                    c_names = data.get("category_names", [])
                    category_name = c_names[0] if c_names else "Услуга"
                    
                    # Use username if available, otherwise use phone
                    client_username = user.get('username')
                    if client_username:
                        client_info = f"@{client_username}"
                    else:
                        client_info = phone

                    notify_text = get_text(
                        "master_notify_new_order",
                        master_lang,
                        category=category_name,
                        client_info=client_info
                    )
                    try:
                        await bot.send_message(master_user['telegram_id'], notify_text)
                    except Exception as e:
                        logger.error(f"Could not notify master {pending_master_id}: {e}")
    
    await clear_state_preserve_sticker(state)


@router.message(ClientChangePhone.waiting_contact, F.contact)
async def phone_change_contact(message: Message, state: FSMContext, user: dict = None):
    """Handle shared contact for phone change"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    phone = normalize_phone(message.contact.phone_number)
    
    # Update client profile with new verified phone
    profile = await db.get_client_profile(user['id'])
    if profile:
        await db.update_client_phone(user['id'], phone, phone_verified=True)
    else:
        await db.create_client_profile(user['id'], phone=phone, phone_verified=True)
    
    await message.answer(
        get_text("phone_updated", lang), 
        reply_markup=get_remove_keyboard()
    )
    await clear_state_preserve_sticker(state)


@router.message(ClientPhoneVerification.waiting_contact)
async def phone_verification_text(message: Message, state: FSMContext, user: dict = None):
    """Handle text input during phone verification - remind to use button"""
    lang = user.get('language', 'ru') if user else 'ru'
    await message.answer(
        get_text("share_phone_prompt", lang),
        reply_markup=get_share_phone_keyboard(lang)
    )


@router.message(ClientChangePhone.waiting_contact)
async def phone_change_text(message: Message, state: FSMContext, user: dict = None):
    """Handle text input during phone change - remind to use button"""
    lang = user.get('language', 'ru') if user else 'ru'
    await message.answer(
        get_text("phone_change_prompt", lang),
        reply_markup=get_share_phone_keyboard(lang)
    )

