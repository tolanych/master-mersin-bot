# ================================
# keyboards.py — Inline/Reply Keyboards
# ================================

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import DISTRICTS, CATEGORIES, CATEGORY_GROUPS
from utils.i18n import get_text, get_category_name, get_district_name
import globals

async def get_main_menu_keyboard(user: dict = None):
    """Main menu for clients (and general users).
    
    Extracts all needed data from user dict:
    - language
    - is_master flag
    - master_status
    - active_orders_count (fetched from DB)
    """
    # Extract user data
    lang = user.get('language', 'ru') if user else 'ru'
    is_master = user.get('is_master', False) if user else False
    master_status = user.get('master_status') if user else None
    user_id = user.get('id') if user else None
    
    # Fetch active orders count from database
    active_orders_count = 0
    if user_id:
        db = globals.get_db()
        active_orders_count = await db.get_active_orders_count(user_id)
    
    # Use active orders button text if there are active orders
    orders_text_key = "menu_my_orders_active" if active_orders_count > 0 else "menu_my_orders"
    
    buttons = [
        [InlineKeyboardButton(text=get_text("menu_find_master", lang), callback_data="menu_find_master")],
        [InlineKeyboardButton(text=get_text("menu_concierge", lang), callback_data="menu_concierge")],
        [InlineKeyboardButton(text=get_text(orders_text_key, lang), callback_data="menu_my_orders")],
    ]
    
    if is_master:
        # Show Master Profile button
        buttons.append([InlineKeyboardButton(text=get_text("menu_master_profile", lang), callback_data="menu_profile")])
        if master_status in ["pending", "active_free", "active_premium"]:
            buttons.append([InlineKeyboardButton(text=get_text("menu_premium", lang), callback_data="menu_premium")])
    else:
        # Show Become Master button
        buttons.append([InlineKeyboardButton(text=get_text("menu_become_master", lang), callback_data="become_master")])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_request_submitted_keyboard(request_id: int, lang: str = "ru"):
    """Keyboard shown after a client submits a service request."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_remind", lang), callback_data=f"client_remind_{request_id}")],
        [InlineKeyboardButton(text=get_text("btn_menu", lang), callback_data="back_main_menu")],
    ])


async def get_categories_keyboard_v2(parent_id: int = None, selected_ids: list = None, lang: str = "ru"):
    """New hierarchical category keyboard supporting N-levels and short names."""
    if selected_ids is None:
        selected_ids = []
    
    db = globals.get_db()
    categories = await db.get_categories(parent_id)
    
    buttons = []
    for cat in categories:
        cat_id = cat['id']
        key = cat['key_field']
        short_key = cat.get('short_key_field')
        has_children = cat.get('child_count', 0) > 0
        
        if has_children:
            # Navigation button
            name = get_category_name(key, lang)
            buttons.append(
                InlineKeyboardButton(text=f"📁 {name}", callback_data=f"cat_{cat_id}")
            )
        else:
            # Selection button (leaf)
            # Use short name for selection buttons if available
            display_key = short_key if short_key else key
            name = get_category_name(display_key, lang)
            status = "✅" if cat_id in selected_ids else "⬜"
            buttons.append(
                InlineKeyboardButton(text=f"{status} {name}", callback_data=f"sel_{cat_id}")
            )
            
    keyboard = []
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i+2])
        
    # Bottom row buttons
    bottom_row = []
    
    # Back button logic
    if parent_id is None:
        bottom_row.append(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu"))
    else:
        parent_cat = await db.get_category(parent_id)
        if parent_cat and parent_cat['parent_id']:
            back_data = f"cat_{parent_cat['parent_id']}"
        else:
            back_data = "menu_find_master" # Back to root
        bottom_row.append(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=back_data))
    
    # Done button (if anything is selected)
    if selected_ids:
        bottom_row.append(InlineKeyboardButton(text=get_text("btn_done", lang), callback_data="service_done"))
        
    if bottom_row:
        keyboard.append(bottom_row)
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_client_districts_keyboard(selected=None, lang: str = "ru"):
    """Multi-select districts for client request flow."""
    if selected is None:
        selected = []
    buttons = []
    for i, district_key in enumerate(DISTRICTS):
        status = "✅" if i in selected else "⬜"
        district_name = get_district_name(district_key, lang)
        buttons.append(
            InlineKeyboardButton(text=f"{status} {district_name}", callback_data=f"cdistrict_{i}")
        )
    keyboard = []
    for i in range(0, len(buttons), 2):
        keyboard.append(buttons[i:i+2])
    keyboard.append([InlineKeyboardButton(text=get_text("btn_done", lang), callback_data="cdistrict_done")])
    keyboard.append([InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_to_services")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_urgency_keyboard(lang: str = "ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("urgency_urgent", lang), callback_data="urgency_urgent")],
        [InlineKeyboardButton(text=get_text("urgency_soon", lang), callback_data="urgency_soon")],
        [InlineKeyboardButton(text=get_text("urgency_flexible", lang), callback_data="urgency_flexible")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_to_districts")],
    ])


def get_budget_keyboard(lang: str = "ru"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("budget_cheap", lang), callback_data="budget_cheap")],
        [InlineKeyboardButton(text=get_text("budget_normal", lang), callback_data="budget_normal")],
        [InlineKeyboardButton(text=get_text("budget_quality", lang), callback_data="budget_quality")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_to_urgency")],
    ])


def get_concierge_topics_keyboard(selected=None, lang: str = "ru"):
    if selected is None:
        selected = []
        
    topics = [
        "concierge_keys",
        "concierge_cleaning",
        "concierge_tenants",
        "concierge_bills",
        "concierge_meetings",
        "concierge_other"
    ]
    
    buttons = []
    for topic in topics:
        status = "✅" if topic in selected else "⬜"
        buttons.append([InlineKeyboardButton(
            text=f"{status} {get_text(topic, lang)}",
            callback_data=f"concierge_toggle_{topic}"
        )])
        
    buttons.append([InlineKeyboardButton(text=get_text("btn_done", lang), callback_data="concierge_done")])
    buttons.append([InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_districts_keyboard():
    """Select district"""
    buttons = []
    for i, district in enumerate(DISTRICTS):
        buttons.append(InlineKeyboardButton(
            text=f"📍 {district}",
            callback_data=f"district_{i}"
        ))
    
    # 2 columns
    keyboard = []
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_categories_keyboard():
    """Select service category"""
    buttons = []
    for i, cat in enumerate(CATEGORIES):
        buttons.append(InlineKeyboardButton(
            text=f"🛠️ {cat}",
            callback_data=f"category_{i}"
        ))
    
    # 2 columns
    keyboard = []
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        keyboard.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_masters_keyboard(masters, page: int = 0, total_pages: int = 1, lang: str = "ru"):
    """Display master list as buttons with pagination"""
    keyboard = []
    
    for master in masters:
        name = master.get('name', 'Master')
        status = master.get('status', 'pending')
        rating = master.get('rating', 0.0)
        
        # Status symbols
        status_symbol = "👻" # Default for pending
        if status == 'active_premium':
            status_symbol = "🔧💎"
        elif status == 'active_free':
            status_symbol = "🔧"
        elif status == 'pending':
            status_symbol = "👻"
        elif status == 'blocked':
            status_symbol = "🚫"
            
        # Rating string
        rating_str = f" ⭐️{rating:.1f}" if rating and rating > 0 else ""
        
        keyboard.append([InlineKeyboardButton(
            text=f"{status_symbol} {name}{rating_str}",
            callback_data=f"master_profile_{master['id']}"
        )])
    
    # Pagination buttons
    if total_pages > 1:
        pagination_row = []
        # Prev button
        if page > 0:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data="masters_page_prev"))
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop")) # Spacer
            
        # Page indicator
        pagination_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
        
        # Next button
        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data="masters_page_next"))
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop")) # Spacer
            
        keyboard.append(pagination_row)
    
    # Add "Add Master" button and potentially a Back button for the list itself
    keyboard.append([InlineKeyboardButton(text=get_text("add_master", lang), callback_data="add_master")])
    
    # Add navigation buttons
    keyboard.append([
        InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="menu_find_master"),
        InlineKeyboardButton(text=get_text("btn_menu", lang), callback_data="back_main_menu"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_master_profile_keyboard(master_id, lang: str = "ru"):
    """Master profile actions"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("master_contact_btn", lang), callback_data=f"master_contact_{master_id}"),
            InlineKeyboardButton(text=get_text("master_reviews_btn", lang), callback_data=f"master_reviews_{master_id}"),
        ],
        [InlineKeyboardButton(text=get_text("btn_reputation", lang), callback_data=f"master_reputation_{master_id}")],
        [InlineKeyboardButton(text=get_text("btn_report", lang), callback_data=f"master_report_{master_id}")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_to_results")], 
    ])

def get_order_confirmation_keyboard(master_id):
    """Confirm order start"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("btn_confirm", "ru"), callback_data=f"order_confirm_{master_id}"),
            InlineKeyboardButton(text=get_text("btn_cancel", "ru"), callback_data="order_cancel"),
        ],
    ])

def get_order_completion_keyboard(order_id, lang: str = "ru"):
    """Mark order as completed"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("order_complete_button", lang), callback_data=f"order_complete_{order_id}")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")],
    ])

def get_rating_keyboard(order_id):
    """Select rating (1-5 stars)"""
    keyboard = []
    for i in range(1, 6):
        keyboard.append(InlineKeyboardButton(
            text=f"{'⭐' * i}",
            callback_data=f"rating_{order_id}_{i}"
        ))
    return InlineKeyboardMarkup(inline_keyboard=[keyboard])

def get_yes_no_keyboard(action, lang: str = "ru"):
    """Yes/No confirmation (language aware)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("btn_confirm", lang), callback_data=f"confirm_{action}"),
            InlineKeyboardButton(text=get_text("btn_cancel", lang), callback_data=f"cancel_{action}"),
        ],
    ])

def get_add_master_keyboard(lang: str = "ru"):
    """Add new master form (language aware)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("add_master", lang), callback_data="add_master")],
    ])

def get_master_districts_keyboard(selected=None, lang: str = "ru"):
    """Multi-select districts for master registration"""
    if selected is None:
        selected = []
    
    buttons = []
    for i, district_key in enumerate(DISTRICTS):
        status = "✅" if i in selected else "⬜"
        district_name = get_district_name(district_key, lang)
        buttons.append(InlineKeyboardButton(
            text=f"{status} {district_name}",
            callback_data=f"mdistrict_{i}"
        ))
    
    keyboard = []
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text=get_text("btn_done", lang), callback_data="mdistrict_done")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_approve_reject_keyboard(master_id, lang: str = "ru"):
    """Admin approve/reject master (language aware)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("btn_confirm", lang), callback_data=f"admin_approve_{master_id}"),
            InlineKeyboardButton(text=get_text("btn_cancel", lang), callback_data=f"admin_reject_{master_id}"),
        ],
    ])

def get_language_keyboard(lang: str = "ru"):
    """Select language (language-aware labels)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_text("lang_ru", lang), callback_data="lang_ru"),
            InlineKeyboardButton(text=get_text("lang_tr", lang), callback_data="lang_tr"),
            InlineKeyboardButton(text=get_text("lang_en", lang), callback_data="lang_en"),
        ],
    ])


def get_share_phone_keyboard(lang: str = "ru"):
    """Keyboard with button to share phone number via Telegram contact"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_text("btn_share_phone", lang), request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_remove_keyboard():
    """Remove reply keyboard"""
    return ReplyKeyboardRemove()


def get_client_profile_keyboard(lang: str = "ru"):
    """Client profile action buttons"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_history", lang), callback_data="client_history")],
        [InlineKeyboardButton(text=get_text("btn_change_phone", lang), callback_data="client_change_phone")],
        [InlineKeyboardButton(text=get_text("btn_my_reviews", lang), callback_data="client_my_reviews")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")],
    ])


def get_master_own_profile_keyboard(master_id, lang: str = "ru"):
    """Master's own profile action buttons"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_reputation", lang), callback_data=f"master_reputation_{master_id}")],
        [InlineKeyboardButton(text=get_text("btn_edit_info", lang), callback_data="master_edit_info")],
        [InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")],
    ])


def get_client_rating_keyboard(order_id: int):
    """Keyboard for master to rate client (1-5 scale)"""
    keyboard = []
    for i in range(1, 6):
        keyboard.append(InlineKeyboardButton(
            text=f"{'⭐' * i}",
            callback_data=f"client_rating_{order_id}_{i}"
        ))
    return InlineKeyboardMarkup(inline_keyboard=[keyboard])


def get_skip_feedback_keyboard(order_id: int, lang: str = "ru"):
    """Keyboard to skip leaving feedback about client"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_text("btn_skip", lang), callback_data=f"skip_client_feedback_{order_id}")]
    ])


def get_master_client_feedback_checklist_keyboard(order_id: int, criteria: list, selected_ids=None, lang: str = "ru"):
    """Multi-select checklist for master to rate client using dynamic criteria"""
    if selected_ids is None:
        selected_ids = []
        
    keyboard = []
    
    current_group = None
    for item in criteria:
        # Group headers
        if item['group_key'] != current_group:
            current_group = item['group_key']
            group_label = get_text(current_group, lang) if current_group else "---"
            keyboard.append([InlineKeyboardButton(text=f"{group_label}", callback_data="noop")])
        
        status = "☑️" if item['id'] in selected_ids else "⬜️"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {get_text(item['code_key'], lang)}",
            callback_data=f"fdbk_toggle_{item['id']}"
        )])
        
    keyboard.append([InlineKeyboardButton(text=get_text("btn_done", lang), callback_data=f"fdbk_done_{order_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_client_master_feedback_checklist_keyboard(order_id: int, criteria: list, selected_ids=None, lang: str = "ru"):
    """Multi-select checklist for client to rate master using dynamic criteria"""
    if selected_ids is None:
        selected_ids = []
        
    keyboard = []
    
    current_group = None
    for item in criteria:
        if item['group_key'] != current_group:
            current_group = item['group_key']
            group_label = get_text(current_group, lang) if current_group else "---"
            keyboard.append([InlineKeyboardButton(text=f"{group_label}", callback_data="noop")])
            
        status = "☑️" if item['id'] in selected_ids else "⬜️"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {get_text(item['code_key'], lang)}",
            callback_data=f"mfdbk_toggle_{item['id']}"
        )])
        
    keyboard.append([InlineKeyboardButton(text=get_text("btn_done", lang), callback_data=f"mfdbk_done_{order_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_premium_keyboard(lang: str = "ru", is_active: bool = False):
    """Premium status actions"""
    buttons = []
    
    if not is_active:
        buttons.append([InlineKeyboardButton(text=get_text("btn_buy_premium", lang), callback_data="premium_buy")])
        buttons.append([InlineKeyboardButton(text=get_text("btn_i_paid", lang), callback_data="premium_i_paid")])
    else:
        # If active, maybe show contact admin to extend or similar
        # For now, just the paid button if they want to pay again
        buttons.append([InlineKeyboardButton(text=get_text("btn_i_paid", lang), callback_data="premium_i_paid")])
    
    buttons.append([InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="back_main_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_orders_menu_keyboard(active_orders: list, has_completed_history: bool, lang: str = "ru"):
    """Keyboard for orders page with completion buttons"""
    buttons = []
    
    # Show completion buttons based on number of active orders
    if len(active_orders) == 1:
        # Single active order - show simple button
        buttons.append([InlineKeyboardButton(
            text=get_text("btn_complete_work", lang),
            callback_data=f"order_complete_{active_orders[0]['id']}"
        )])
    elif len(active_orders) > 1:
        # Multiple active orders - show buttons with IDs
        for order in active_orders:
            buttons.append([InlineKeyboardButton(
                text=get_text("btn_complete_work_id", lang, id=order['id']),
                callback_data=f"order_complete_{order['id']}"
            )])
    
    # Show history button only if there are completed orders
    if has_completed_history:
        buttons.append([InlineKeyboardButton(
            text=get_text("btn_order_history", lang),
            callback_data="orders_history_page_0"
        )])
    
    # Back to main menu
    buttons.append([InlineKeyboardButton(
        text=get_text("btn_back", lang),
        callback_data="back_main_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_orders_history_keyboard(page: int, total_pages: int, lang: str = "ru", back_callback: str = "menu_my_orders"):
    """Keyboard for order history with pagination"""
    buttons = []
    
    # Pagination row
    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"orders_history_page_{page-1}"))
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
        
        pagination_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
        
        if page < total_pages - 1:
            pagination_row.append(InlineKeyboardButton(text="➡️", callback_data=f"orders_history_page_{page+1}"))
        else:
            pagination_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
        
        buttons.append(pagination_row)
    
    # Back button
    buttons.append([InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=back_callback)])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
