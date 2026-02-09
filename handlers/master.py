# ================================
# handlers/master.py — Master Commands & Registration Flow
# ================================

import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


from config import DISTRICTS, CATEGORIES, ADMIN_IDS
from states import MasterRegistration, MasterRateClient, MasterEdit
from keyboards import (
    get_master_districts_keyboard,
    get_categories_keyboard_v2,
    get_yes_no_keyboard,
    get_client_rating_keyboard,
    get_master_client_feedback_checklist_keyboard,
    get_share_phone_keyboard,
    get_main_menu_keyboard
)
from utils.i18n import get_text, get_category_name, get_district_name
from utils.phone_utils import normalize_phone, is_valid_phone
import globals
from services.stickers import replace_sticker, StickerEvent, clear_state_preserve_sticker


db = globals.get_db()
bot = globals.get_bot()  # noqa: F401 (reserved for future notifications)

logger = logging.getLogger(__name__)
router = Router()





_BACK_WORDS = {
    "назад",
    "⬅️ назад",
    "back",
    "geri",
    "🔙",
}


def _is_back(text: str | None) -> bool:
    if not text:
        return False
    return text.strip().lower() in _BACK_WORDS


# ====== ROLE: MASTER ======
@router.callback_query(F.data == "become_master")
async def become_master_start(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """User selects 'Become Master' → start master registration if needed."""
    # user_id = await db.get_or_create_user(...) # User should already exist if they are here
    user_id = user['id'] if user else None
    
    # Note: We don't set is_master=True here yet, only after registration
    lang = user.get('language', 'ru') if user else 'ru'

    # Duplicate prevention
    existing = await db.get_master_by_user_id(user_id)
    if existing:
        text = get_text("master_profile_exists", lang)
        await callback.message.edit_text(text)
        await clear_state_preserve_sticker(state)
        return

    text = get_text("master_reg_name", lang)
    await callback.message.edit_text(text)
    await state.set_state(MasterRegistration.name)




# ====== CONFIRMATION ======
@router.callback_query(MasterRegistration.confirmation, F.data == "confirm_master_reg")
async def master_reg_confirm(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    # Duplicate prevention (race-safe)
    existing = await db.get_master_by_user_id(user["id"] if user else None)
    if existing:
        await callback.message.edit_text(get_text("master_profile_exists", lang))
        await clear_state_preserve_sticker(state)
        return

    data = await state.get_data()
    
    # Convert district indices to district keys and then to IDs
    selected_district_indices = data.get("selected_districts", [])
    district_keys = [DISTRICTS[i] for i in selected_district_indices if 0 <= i < len(DISTRICTS)]
    
    # Resolve category IDs
    category_ids = data.get("selected_categories", [])
    # We already have IDs, no need to convert from keys unless we need keys for something else.
    # But create_master and update_master_profile take IDs.
    
    district_ids = []
    for dist_key in district_keys:
        # Use cache
        dist_id = globals.cache_service.get_district_id(dist_key)
        if dist_id:
            district_ids.append(dist_id)

    try:
        await db.create_master(
            user_id=user["id"] if user else None,
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            description=data.get("description", ""),
            categories=category_ids,
            districts=district_ids,
            status="pending",
            source="myself"
        )
        # Set is_master flag to True so user sees "My Profile"
        if user:
            await db.set_user_master(user['id'], True)
            
    except Exception:
        logger.exception("Failed to create master profile")
        await callback.message.edit_text(get_text("error", lang))
        await clear_state_preserve_sticker(state)
        return

    await replace_sticker(callback.message, state, StickerEvent.SUCCESS)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(get_text("master_registration_submitted", lang))
    # State Cleanup
    await clear_state_preserve_sticker(state)


# ====== NAME ======
@router.message(MasterRegistration.name)
async def master_reg_name(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    if _is_back(message.text):
        # Go back to main menu
        from keyboards import get_main_menu_keyboard
        text = get_text("main_menu", lang)
        
        await replace_sticker(message, state, StickerEvent.CATEGORIES)
        await message.answer(text, reply_markup=await get_main_menu_keyboard(user=user))
        await clear_state_preserve_sticker(state)
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer(get_text("master_reg_name", lang))
        return

    await state.update_data(name=name)
    await message.answer(get_text("master_reg_phone", lang))
    await state.set_state(MasterRegistration.phone)


# ====== PHONE ======
@router.message(MasterRegistration.phone)
async def master_reg_phone(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    if _is_back(message.text):
        await message.answer(get_text("master_reg_name", lang))
        await state.set_state(MasterRegistration.name)
        return

    raw_phone = (message.text or "").strip()
    if not is_valid_phone(raw_phone):
        await message.answer(get_text("invalid_phone", lang))
        return

    phone = normalize_phone(raw_phone)
    # Check for existing phone
    existing_master = await db.get_master_by_phone(phone)
    print(phone)
    if existing_master:
        if existing_master.get('user_id') == -1:
            # Handle unlinked master profile
            # Point to admins using tg://user?id=... format as we only have IDs in config
            admin_links = '@philipp1993'#"\n".join([f'<a href="tg://user?id={aid}">👨‍💼moder{aid}</a>' for aid in ADMIN_IDS])
            text = get_text("claim_master_prompt", lang, admin_links=admin_links)
            
            await state.update_data(claim_master_id=existing_master['id'])
            await state.update_data(claim_master_phone=phone)
            await message.answer(text, reply_markup=get_share_phone_keyboard(lang), parse_mode="HTML")
            await state.set_state(MasterRegistration.claiming_master)
            return

        await message.answer(get_text("phone_already_registered", lang))
        return

    await state.update_data(phone=phone)
    await message.answer(get_text("master_districts", lang), reply_markup=get_master_districts_keyboard(lang=lang))
    await state.set_state(MasterRegistration.districts)


# ====== DISTRICTS (multi-select) ======
@router.callback_query(MasterRegistration.districts, F.data.startswith("mdistrict_"))
async def master_reg_districts(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Multi-select districts. Pattern copied from ClientAddMaster.master_districts."""
    lang = user.get('language', 'ru') if user else 'ru'

    data = await state.get_data()
    selected = data.get("selected_districts", [])

    if callback.data == "mdistrict_done":
        if not selected:
            await callback.answer(get_text("select_at_least_one_district", lang), show_alert=True)
            return

        text = get_text("master_categories", lang)
        # Use v2 keyboard
        markup = await get_categories_keyboard_v2(parent_id=None, selected_ids=[], lang=lang)
        await callback.message.edit_text(text, reply_markup=markup)
        await state.set_state(MasterRegistration.categories)
    else:
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
        await callback.message.edit_reply_markup(reply_markup=get_master_districts_keyboard(selected, lang))


# ====== CATEGORIES (hierarchical multi-select) ======
@router.callback_query(StateFilter(MasterRegistration.categories, MasterEdit.categories), F.data.startswith("cat_"))
async def master_navigate_categories(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    cat_id = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])
    
    markup = await get_categories_keyboard_v2(parent_id=cat_id, selected_ids=selected_ids, lang=lang)
    await callback.message.edit_text(get_text("master_categories", lang), reply_markup=markup)

@router.callback_query(StateFilter(MasterRegistration.categories, MasterEdit.categories), F.data.startswith("sel_"))
async def master_toggle_category_selection(callback: CallbackQuery, state: FSMContext, user: dict = None):
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

@router.callback_query(StateFilter(MasterRegistration.categories, MasterEdit.categories), F.data == "service_done")
async def master_categories_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    selected_ids = data.get("selected_category_ids", [])

    if not selected_ids:
        await callback.answer(get_text("select_at_least_one_category", lang), show_alert=True)
        return

    # Store IDs for registration/edit
    await state.update_data(selected_categories=selected_ids)

    current_state = await state.get_state()
    if current_state == MasterRegistration.categories:
        text = get_text("master_reg_description", lang)
        await callback.message.edit_text(text)
        await state.set_state(MasterRegistration.description)
    else: # MasterEdit.categories
        await callback.message.edit_text(get_text("master_districts", lang), reply_markup=get_master_districts_keyboard(lang=lang))
        await state.set_state(MasterEdit.districts)


# ====== DESCRIPTION ======
@router.message(MasterRegistration.description)
async def master_reg_description(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    if _is_back(message.text):
        # Go back to categories selection.
        data = await state.get_data()
        selected_ids = data.get("selected_category_ids", [])
        markup = await get_categories_keyboard_v2(parent_id=None, selected_ids=selected_ids, lang=lang)
        await message.answer(get_text("master_categories", lang), reply_markup=markup)
        await state.set_state(MasterRegistration.categories)
        return

    description = (message.text or "").strip()
    if not description:
        await message.answer(get_text("master_reg_description", lang))
        return

    # Length limit: 100 for registration
    limit = 100
    if len(description) > limit:
        await message.answer(get_text("description_too_long", lang, limit=limit, length=len(description)))
        return

    await state.update_data(description=description)
    data = await state.get_data()
    
    # Resolve names for confirmation display
    districts = [get_district_name(DISTRICTS[i], lang) for i in data.get("selected_districts", []) if 0 <= i < len(DISTRICTS)]
    
    selected_category_ids = data.get("selected_categories", [])
    categories = []
    for cid in selected_category_ids:
        cat = await db.get_category(cid)
        if cat:
            categories.append(get_category_name(cat['key_field'], lang))

    text = get_text(
        "master_reg_confirm",
        lang,
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        districts=", ".join(districts) if districts else "-",
        categories=", ".join(categories) if categories else "-",
        description=description,
    )
    await message.answer(text, reply_markup=get_yes_no_keyboard("master_reg", lang))
    await state.set_state(MasterRegistration.confirmation)





@router.callback_query(MasterRegistration.confirmation, F.data == "cancel_master_reg")
async def master_reg_cancel(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'

    await callback.message.edit_text(get_text("master_registration_cancelled", lang))
    await clear_state_preserve_sticker(state)


@router.message(MasterRegistration.claiming_master, F.contact)
async def master_claim_contact(message: Message, state: FSMContext, user: dict = None):
    """Handle shared contact for claiming an unlinked master profile during registration"""
    lang = user.get('language', 'ru') if user else 'ru'
    shared_phone = normalize_phone(message.contact.phone_number)
    
    data = await state.get_data()
    master_phone = normalize_phone(data.get("claim_master_phone"))
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


@router.message(MasterRegistration.claiming_master)
async def master_claim_text(message: Message, state: FSMContext, user: dict = None):
    """Remind to share contact during claiming process"""
    lang = user.get('language', 'ru') if user else 'ru'
    admin_links = ", ".join([f'<a href="tg://user?id={aid}">👨‍💼moder{aid}</a>' for aid in ADMIN_IDS])
    await message.answer(
        get_text("claim_master_prompt", lang, admin_links=admin_links),
        reply_markup=get_share_phone_keyboard(lang),
        parse_mode="HTML"
    )


# ====== STATE RECOVERY: ignore unrelated callbacks gracefully ======
@router.callback_query(StateFilter(MasterRegistration))
async def master_reg_unexpected_callback(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Catch-all for unexpected callbacks during registration."""
    lang = user.get('language', 'ru') if user else 'ru'
    await callback.answer(get_text("error", lang), show_alert=True)


# ====== MASTER EDIT PROFILE ======
@router.callback_query(F.data == "master_edit_info")
async def master_edit_start(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Start the multi-step editing process."""
    lang = user.get('language', 'ru') if user else 'ru'
    
    if not user or not user.get('is_master') or not user.get('master_id'):
        await callback.answer(get_text("error", lang), show_alert=True)
        return

    await state.update_data(master_id=user['master_id'])
    
    # Step 1: Phone
    await callback.message.edit_text(get_text("master_reg_phone", lang))
    await state.set_state(MasterEdit.phone)


@router.message(MasterEdit.phone)
async def master_edit_phone(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    raw_phone = (message.text or "").strip()
    
    if _is_back(message.text):
        # Go back to profile
        await clear_state_preserve_sticker(state)
        from handlers.client import cmd_profile
        await cmd_profile(message, state)
        return

    if not is_valid_phone(raw_phone):
        await message.answer(get_text("invalid_phone", lang))
        return

    phone = normalize_phone(raw_phone)
    # Check for existing phone (excluding self)
    data = await state.get_data()
    master_id = data.get("master_id")
    existing_master = await db.get_master_by_phone(phone)
    if existing_master and existing_master['id'] != master_id:
        await message.answer(get_text("phone_already_registered", lang))
        return

    await state.update_data(phone=phone)
    await message.answer(get_text("master_reg_name", lang))
    await state.set_state(MasterEdit.name)


@router.message(MasterEdit.name)
async def master_edit_name(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    name = (message.text or "").strip()
    
    if _is_back(message.text):
        await message.answer(get_text("master_reg_phone", lang))
        await state.set_state(MasterEdit.phone)
        return

    if not name:
        await message.answer(get_text("master_reg_name", lang))
        return

    await state.update_data(name=name)
    markup = await get_categories_keyboard_v2(parent_id=None, selected_ids=[], lang=lang)
    await message.answer(get_text("master_categories", lang), reply_markup=markup)
    await state.set_state(MasterEdit.categories)


# Categories handlers shared above with navigate_categories and toggle_category_selection


@router.callback_query(MasterEdit.districts, F.data.startswith("mdistrict_"))
async def master_edit_districts(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    selected = data.get("selected_districts", [])

    if callback.data == "mdistrict_done":
        if not selected:
            await callback.answer(get_text("select_at_least_one_district", lang), show_alert=True)
            return

        # Check premium status for prompt
        # user already injected
        master = await db.get_master_by_user_id(user['id'])
        
        if master and master.get('status') == 'active_premium':
            text = get_text("master_edit_description_premium", lang)
        else:
            text = get_text("master_edit_description", lang)
            
        await callback.message.edit_text(text)
        await state.set_state(MasterEdit.description)
    else:
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
        await callback.message.edit_reply_markup(reply_markup=get_master_districts_keyboard(selected, lang))


@router.message(MasterEdit.description)
async def master_edit_description(message: Message, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    description = (message.text or "").strip()
    
    if _is_back(message.text):
        data = await state.get_data()
        selected = data.get("selected_districts", [])
        await message.answer(get_text("master_districts", lang), reply_markup=get_master_districts_keyboard(selected, lang))
        await state.set_state(MasterEdit.districts)
        return

    if not description:
        await message.answer(get_text("master_reg_description", lang))
        return

    # Check premium status for limit
    # use injected user
    master = await db.get_master_by_user_id(user['id'])
    
    limit = 100
    if master and master.get('status') == 'active_premium':
        limit = 300
        
    if len(description) > limit:
        await message.answer(get_text("description_too_long", lang, limit=limit, length=len(description)))
        return

    await state.update_data(description=description)
    data = await state.get_data()
    
    # Resolve names for confirmation display
    districts = [get_district_name(DISTRICTS[i], lang) for i in data.get("selected_districts", []) if 0 <= i < len(DISTRICTS)]
    
    selected_category_ids = data.get("selected_categories", [])
    categories = []
    for cid in selected_category_ids:
        cat = await db.get_category(cid)
        if cat:
            categories.append(get_category_name(cat['key_field'], lang))

    text = get_text(
        "master_reg_confirm",
        lang,
        name=data.get("name", ""),
        phone=data.get("phone", ""),
        districts=", ".join(districts) if districts else "-",
        categories=", ".join(categories) if categories else "-",
        description=description,
    )
    await message.answer(text, reply_markup=get_yes_no_keyboard("master_edit", lang))
    await state.set_state(MasterEdit.confirmation)


@router.callback_query(MasterEdit.confirmation, F.data == "confirm_master_edit")
async def master_edit_confirm(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    master_id = data.get("master_id")
    
    # Resolve IDs
    selected_district_indices = data.get("selected_districts", [])
    district_keys = [DISTRICTS[i] for i in selected_district_indices if 0 <= i < len(DISTRICTS)]
    
    district_ids = []
    for dist_key in district_keys:
        # Use cache
        dist_id = globals.cache_service.get_district_id(dist_key)
        if dist_id: district_ids.append(dist_id)

    category_ids = data.get("selected_categories", [])

    try:
        await db.update_master_profile(
            master_id=master_id,
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            description=data.get("description", ""),
            categories=category_ids,
            districts=district_ids
        )
        await replace_sticker(callback.message, state, StickerEvent.SUCCESS)
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        await callback.message.answer(get_text("phone_updated", lang)) # Reusing "phone_updated" or similar success message
    except Exception:
        logger.exception("Failed to update master profile")
        await callback.message.edit_text(get_text("error", lang))
    
    await clear_state_preserve_sticker(state)
    # Go back to profile
    from handlers.client import cmd_profile
    await cmd_profile(callback, state)


@router.callback_query(MasterEdit.confirmation, F.data == "cancel_master_edit")
async def master_edit_cancel(callback: CallbackQuery, state: FSMContext, user: dict = None):
    lang = user.get('language', 'ru') if user else 'ru'
    await callback.message.edit_text(get_text("master_registration_cancelled", lang))
    await clear_state_preserve_sticker(state)
    from handlers.client import cmd_profile
    await cmd_profile(callback, state)


# ====== MASTER RATES CLIENT ======
@router.callback_query(F.data.startswith("rate_client_"))
async def start_rate_client(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Master starts feedback process for client (checklist first)"""
    lang = user.get('language', 'ru') if user else 'ru'
    order_id = int(callback.data.split("_")[2])
    
    # Fetch criteria for Master -> Client (role_client=False)
    criteria = await db.get_criteria(role_client=False)
    
    await state.update_data(order_id=order_id, criteria=criteria, selected_criteria_ids=[])
    
    await callback.message.edit_text(
        get_text("master_client_feedback", lang),
        reply_markup=get_master_client_feedback_checklist_keyboard(order_id, criteria=criteria, selected_ids=[], lang=lang)
    )
    await state.set_state(MasterRateClient.feedback)


@router.callback_query(MasterRateClient.rating, F.data.startswith("client_rating_"))
async def master_client_rating(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Final step: master selects rating and everything is saved"""
    lang = user.get('language', 'ru') if user else 'ru'
    
    parts = callback.data.split("_")
    order_id = int(parts[2])
    rating = int(parts[3])

    data = await state.get_data()
    selected_ids = data.get("selected_criteria_ids", [])
    
    # Save rating using existing method
    await db.rate_client(order_id, rating) # Note: we stop passing legacy feedback JSON
    
    # Save reputation votes
    await db.save_votes(from_client=False, order_id=order_id, criterion_ids=selected_ids)
    
    await replace_sticker(callback.message, state, StickerEvent.FEEDBACK)
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(
        get_text("client_rated", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=get_text("btn_menu", lang), callback_data="back_main_menu")]
        ])
    )
    await clear_state_preserve_sticker(state)


@router.callback_query(MasterRateClient.feedback, F.data.startswith("fdbk_toggle_"))
async def toggle_client_feedback(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Toggle a selection in the feedback checklist with mutual exclusion"""
    lang = user.get('language', 'ru') if user else 'ru'
    try:
        criterion_id = int(callback.data.replace("fdbk_toggle_", ""))
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
    await callback.message.edit_reply_markup(
        reply_markup=get_master_client_feedback_checklist_keyboard(order_id, criteria=criteria, selected_ids=selected_ids, lang=lang)
    )


@router.callback_query(MasterRateClient.feedback, F.data.startswith("fdbk_done_"))
async def master_client_feedback_done(callback: CallbackQuery, state: FSMContext, user: dict = None):
    """Checklist done, now ask for rating stars"""
    lang = user.get('language', 'ru') if user else 'ru'
    data = await state.get_data()
    
    order_id = data.get("order_id")
    
    await callback.message.edit_text(
        get_text("master_rate_client", lang),
        reply_markup=get_client_rating_keyboard(order_id)
    )
    await state.set_state(MasterRateClient.rating)


# Removed master_client_feedback as it is now handled by fdbk_done callback
