# ================================
# config.py — Configuration & Env Vars
# ================================

import os
from dotenv import load_dotenv

load_dotenv()

# ====== Telegram ======
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # https://yourdomain.onrender.com (no /webhook)
PORT = int(os.getenv("PORT", 8000))
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# ====== Payment & Moderation ======
PAYMENT_IBAN = os.getenv("PAYMENT_IBAN", "TR00 0000 0000 0000 0000 0000 00")
PAYMENT_RECIPIENT = os.getenv("PAYMENT_RECIPIENT", "MASTER MERSIN")
MODERATOR_USERNAME = os.getenv("MODERATOR_USERNAME", "@moderator")

# ====== Database ======
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mersin_bot")

# ====== Google Sheets ======
SHEETS_CREDS_JSON = os.getenv("SHEETS_CREDS", "{}")  # Service account JSON as string
SHEETS_ID = os.getenv("SHEETS_ID", "")  # Your Google Sheet ID

# ====== Mersin Districts (config) ======
DISTRICTS = [
    "tashucu",
    "silifke", 
    "tece",
    "erdemli",
    "mezitli",
    "yenisehir",
    "akdeniz",
    "toroslar",
    "mut",
    "aydincik"
]

# ====== Service Categories ======
# NOTE: Now using key fields instead of full bilingual names
# Translation is handled via i18n system
CATEGORIES = [
    # Group: home_living
    "plumbing_install", "plumbing_repair", "electrical_install", "electrical_repair",
    "lighting_install", "socket_install", "furniture_assembly", "handyman_small_repair",
    "doors_install", "windows_repair", "balcon", "boiler_install", "boiler_repair",
    "water_heater_install", "water_heater_repair", "solar_install", "solar_repair",
    "ac_install", "ac_repair", "ac_service", "kitchen_appliance_install", "hood_install",
    "cleaning_basic", "cleaning_deep", "cleaning_after_renovation", "window_cleaning",
    "furniture_dry_cleaning", "carpet_dry_cleaning", "painting", "tiling", "flooring", "drywall",

    # Group: electronics
    "washing_machine_repair", "dishwasher_repair", "fridge_repair", "oven_repair", "tv_repair",
    "phone_repair", "laptop_repair", "pc_repair", "small_electronics_repair", "wifi_setup",
    "cctv_install", "intercom_install", "smart_home_install",

    # Group: auto
    "car_repair", "car_diagnostics", "auto_electrician", "tire_service", "car_wash_detailing",
    "car_rental", "driver_service", "taxi_transfer", "tow_truck",

    # Group: beauty_health
    "haircut_men", "haircut_women", "hair_coloring", "barber", "manicure", "pedicure",
    "nails_extension", "eyelashes", "brows", "cosmetology", "makeup_artist",
    "massage_relax", "depilation", "tattoo", "piercing",

    # Group: home_help
    "babysitter", "housekeeper", "cook_home", "caregiver_elderly", "grocery_delivery",
    "medicine_delivery", "pet_walking",

    # Group: logistics
    "movers", "apartment_moving", "courier", "junk_removal", "storage_service",

    # Group: education
    "language_turkish", "language_other", "school_tutor", "music_guitar", "music_piano",
    "music_vocal", "music_other", "sport_fitness", "sport_yoga", "sport_pilates",
    "sport_swimming", "sport_martial", "it_courses", "design_courses", "driving_instructor",
    "crafts_courses", "other_courses",

    # Group: events
    "event_host", "event_planner", "event_decor", "catering", "dj", "photographer_event",
    "videographer_event", "children_animator", "party_rent",

    # Group: medical_support
    "nurse_home", "rehabilitation", "massage_therapeutic", "medical_consultant",
    "hospital_support", "birth_support", "psychologist",

    # Group: tourism
    "hiking_guide", "tour_guide_city", "excursions", "sup_rental", "bicycle_rental",
    "scooter_rental", "sports_equipment_rental", "boat_trip", "photo_shoot", "video_shoot"
]

# Client UI groups → indices in CATEGORIES
CATEGORY_GROUPS = {
    "home_living": list(range(0, 32)),
    "electronics": list(range(32, 45)),
    "auto": list(range(45, 54)),
    "beauty_health": list(range(54, 69)),
    "home_help": list(range(69, 76)),
    "logistics": list(range(76, 81)),
    "education": list(range(81, 98)),
    "events": list(range(98, 107)),
    "medical_support": list(range(107, 114)),
    "tourism": list(range(114, 124)),
}

# ====== Feature flags ======
ENABLE_PAYMENTS = False  # TODO: Stripe/Yookassa
ENABLE_PREMIUM = False
ENABLE_CHAT = False

# ====== Rate limiting ======
RATE_LIMIT_SECONDS = 2
MAX_REQUESTS_PER_MINUTE = 30

# ====== Cache ======
USER_CACHE_TTL = 300  # 5 minutes
USER_CACHE_MAX_SIZE = 500

# ====== Defaults ======
DEFAULT_LANGUAGE = "ru"
SUPPORTED_LANGUAGES = ["ru", "tr", "en"]

# ====== Logging ======
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
