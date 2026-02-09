# ================================
# states.py — FSM States Definition
# ================================

from aiogram.fsm.state import State, StatesGroup

class ClientSearch(StatesGroup):
    """Legacy client search (kept for backwards compatibility)"""
    select_district = State()
    select_category = State()
    viewing_results = State()


class ClientFindMaster(StatesGroup):
    """Client flow: create a service request"""
    select_group = State()
    select_service = State()
    select_districts = State()  # multi-select
    select_urgency = State()
    select_budget = State()
    phone = State()
    comment = State()
    viewing_results = State()


class ClientConcierge(StatesGroup):
    """Client flow: concierge service request"""
    select_topic = State()
    phone = State()
    name = State()

class ClientReview(StatesGroup):
    """Client leaving review after order completion"""
    what_done = State()
    price = State()
    rating = State()
    feedback = State()
    comment = State()

class ClientAddMaster(StatesGroup):
    """Client adding new master to system"""
    master_name = State()
    master_phone = State()
    master_districts = State()
    master_categories = State()
    confirmation = State()
    claiming_master = State()

class MasterRegistration(StatesGroup):
    """Master registration process"""
    name = State()
    phone = State()
    districts = State()  # multi-select
    categories = State()  # multi-select
    description = State()
    confirmation = State()
    claiming_master = State()

class ClientPhoneVerification(StatesGroup):
    """Client phone verification flow"""
    waiting_contact = State()  # Waiting for contact to be shared


class ClientChangePhone(StatesGroup):
    """Client changing phone number"""
    waiting_contact = State()


class MasterRateClient(StatesGroup):
    """Master rating client after order completion"""
    rating = State()
    feedback = State()


class AdminBulk(StatesGroup):
    """Admin bulk moderation via Sheets"""
    reviewing = State()
    approving = State()
    rejecting = State()

class MasterPremium(StatesGroup):
    """Master premium flow"""
    waiting_screenshot = State()


class MasterEdit(StatesGroup):
    """Master profile edit flow"""
    phone = State()
    name = State()
    categories = State()
    districts = State()
    description = State()
    confirmation = State()
