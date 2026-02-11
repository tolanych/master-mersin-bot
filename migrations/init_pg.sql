-- Schema migrations tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- PostgreSQL Initialization Script

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        TEXT,
    language        TEXT DEFAULT 'ru',
    is_master       BOOLEAN DEFAULT FALSE,
    is_client       BOOLEAN DEFAULT TRUE,
    status          TEXT CHECK (status IN ('active','blocked')) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Masters table
CREATE TABLE IF NOT EXISTS masters (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL, -- references users(id) but allowed -1 for manual
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL,
    description     TEXT NOT NULL,
    source          TEXT CHECK (source IN ('myself', 'user')) NOT NULL,
    status          TEXT CHECK (status IN ('draft', 'pending', 'active_free', 'active_premium', 'blocked')) NOT NULL DEFAULT 'draft',
    rating          FLOAT DEFAULT 0.0,
    premium_until   TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_masters_user_id ON masters(user_id);
CREATE INDEX IF NOT EXISTS idx_masters_status ON masters(status);

-- Client Profiles
CREATE TABLE IF NOT EXISTS client_profiles (
    user_id         INTEGER PRIMARY KEY, -- One profile per user
    phone           TEXT,
    phone_verified  BOOLEAN DEFAULT FALSE,
    rating          FLOAT DEFAULT 5.0,
    total_completed INTEGER DEFAULT 0,
    total_cancelled INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id              SERIAL PRIMARY KEY,
    parent_id       INTEGER REFERENCES categories(id),
    key_field       TEXT UNIQUE NOT NULL,
    short_key_field TEXT
);

-- Districts
CREATE TABLE IF NOT EXISTS districts (
    id          SERIAL PRIMARY KEY,
    key_field   TEXT UNIQUE NOT NULL
);

-- Master Categories (Many-to-Many)
CREATE TABLE IF NOT EXISTS master_categories (
    master_id      INTEGER REFERENCES masters(id) ON DELETE CASCADE,
    category_id    INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    PRIMARY KEY (master_id, category_id)
);

-- Master Districts (Many-to-Many)
CREATE TABLE IF NOT EXISTS master_districts (
    master_id      INTEGER REFERENCES masters(id) ON DELETE CASCADE,
    district_id    INTEGER REFERENCES districts(id) ON DELETE CASCADE,
    PRIMARY KEY (master_id, district_id)
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    client_id       INTEGER NOT NULL, -- references users(id)
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    category_id     INTEGER REFERENCES categories(id),
    status          TEXT NOT NULL DEFAULT 'active', -- active, completed, cancelled
    client_rating   INTEGER, -- Rating given TO client
    rating          INTEGER, -- Rating given TO master
    review_text     TEXT,
    price           INTEGER,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_client_status ON orders(client_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Service Requests (Concierge)
CREATE TABLE IF NOT EXISTS service_requests (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    categories  TEXT,
    phone       TEXT,
    name        TEXT,
    status      TEXT DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Premium Requests
CREATE TABLE IF NOT EXISTS premium_requests (
    id          SERIAL PRIMARY KEY,
    master_id   INTEGER NOT NULL REFERENCES masters(id),
    user_id     INTEGER NOT NULL, 
    status      TEXT DEFAULT 'pending',
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Premium Payments
CREATE TABLE IF NOT EXISTS premium_payments (
    id              SERIAL PRIMARY KEY,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    amount          INTEGER NOT NULL,
    status          TEXT CHECK (status IN ('pending','confirmed','rejected')) NOT NULL,
    admin_id        INTEGER,
    premium_until   TIMESTAMP,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    confirmed_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_premium_payments_master_id ON premium_payments(master_id);

-- Status Logs
CREATE TABLE IF NOT EXISTS status_logs (
    id          SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    changed_by  INTEGER,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Reputation System
CREATE TABLE IF NOT EXISTS reputation_criteria (
    id          SERIAL PRIMARY KEY,
    code_key    TEXT UNIQUE NOT NULL,
    role_client BOOLEAN NOT NULL,
    group_key   TEXT
);

CREATE TABLE IF NOT EXISTS reputation_votes (
    id              SERIAL PRIMARY KEY,
    from_client     BOOLEAN NOT NULL,
    order_id        INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    criterion_id    INTEGER NOT NULL REFERENCES reputation_criteria(id) ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- =============================================
-- Initial Data Seeding
-- =============================================

-- Districts
INSERT INTO districts (key_field) VALUES
('tashucu'), ('silifke'), ('tece'), ('erdemli'),
('mezitli'), ('yenisehir'), ('akdeniz'), ('toroslar'),
('mut'), ('aydincik')
ON CONFLICT (key_field) DO NOTHING;

-- Reputation Criteria
INSERT INTO reputation_criteria (code_key, role_client, group_key) VALUES
('crit_m_on_time', TRUE, 'rep_group_arrival'),
('crit_m_late', TRUE, 'rep_group_arrival'),
('crit_m_no_show', TRUE, 'rep_group_arrival'),
('crit_m_polite', TRUE, 'rep_group_communication'),
('crit_m_tense', TRUE, 'rep_group_communication'),
('crit_m_rude', TRUE, 'rep_group_communication'),
('crit_m_good', TRUE, 'rep_group_result'),
('crit_m_minor_issues', TRUE, 'rep_group_result'),
('crit_m_redo', TRUE, 'rep_group_result'),
('crit_m_as_agreed', TRUE, 'rep_group_agreements'),
('crit_m_changed_on_spot', TRUE, 'rep_group_agreements'),
('crit_m_price_jump', TRUE, 'rep_group_agreements'),
('crit_c_on_time', FALSE, 'rep_group_punctuality'),
('crit_c_late', FALSE, 'rep_group_punctuality'),
('crit_c_no_show', FALSE, 'rep_group_punctuality'),
('crit_c_polite', FALSE, 'rep_group_communication'),
('crit_c_difficult', FALSE, 'rep_group_communication'),
('crit_c_conflict', FALSE, 'rep_group_communication'),
('crit_c_match_desc', FALSE, 'rep_group_agreements'),
('crit_c_changed_details', FALSE, 'rep_group_agreements'),
('crit_c_changed_reqs', FALSE, 'rep_group_agreements'),
('crit_c_paid_ok', FALSE, 'rep_group_payment'),
('crit_c_paid_late', FALSE, 'rep_group_payment'),
('crit_c_payment_dispute', FALSE, 'rep_group_payment')
ON CONFLICT (code_key) DO NOTHING;

-- Categories (Using helper function or specific order to ensure parents exist)
-- Since parents reference self, we must insert in order.
-- NOTE: In PG, IDs are serial, so we can't force explicit IDs easily unless we use OVERRIDING SYSTEM VALUE
-- But better to rely on key_field lookups for parenting.

DO $$
DECLARE
    parent_id_var INTEGER;
BEGIN
    -- Level 1
    INSERT INTO categories (key_field, parent_id) VALUES
    ('v2_home_living', NULL),
    ('v2_electronics', NULL),
    ('v2_auto', NULL),
    ('v2_beauty_health', NULL),
    ('v2_home_help', NULL),
    ('v2_logistics', NULL),
    ('v2_education', NULL),
    ('v2_events', NULL),
    ('v2_medical_support', NULL),
    ('v2_tourism', NULL)
    ON CONFLICT DO NOTHING;

    -- Level 2
    INSERT INTO categories (key_field, parent_id) VALUES
    ('v2_home_sanitary', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_electrical', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_light_sockets', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_assembly_small', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_doors_windows', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_climate', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_kitchen', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_cleaning', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_home_decoration', (SELECT id FROM categories WHERE key_field='v2_home_living')),
    ('v2_electronics_major', (SELECT id FROM categories WHERE key_field='v2_electronics')),
    ('v2_electronics_gadgets', (SELECT id FROM categories WHERE key_field='v2_electronics')),
    ('v2_electronics_internet', (SELECT id FROM categories WHERE key_field='v2_electronics')),
    ('v2_electronics_home_systems', (SELECT id FROM categories WHERE key_field='v2_electronics')),
    ('v2_auto_repair', (SELECT id FROM categories WHERE key_field='v2_auto')),
    ('v2_auto_service', (SELECT id FROM categories WHERE key_field='v2_auto')),
    ('v2_auto_transport', (SELECT id FROM categories WHERE key_field='v2_auto')),
    ('v2_beauty_hair', (SELECT id FROM categories WHERE key_field='v2_beauty_health')),
    ('v2_beauty_nails', (SELECT id FROM categories WHERE key_field='v2_beauty_health')),
    ('v2_beauty_face', (SELECT id FROM categories WHERE key_field='v2_beauty_health')),
    ('v2_beauty_body', (SELECT id FROM categories WHERE key_field='v2_beauty_health')),
    ('v2_home_help_care', (SELECT id FROM categories WHERE key_field='v2_home_help')),
    ('v2_home_help_house', (SELECT id FROM categories WHERE key_field='v2_home_help')),
    ('v2_home_help_errands', (SELECT id FROM categories WHERE key_field='v2_home_help')),
    ('v2_logistics_moving', (SELECT id FROM categories WHERE key_field='v2_logistics')),
    ('v2_logistics_delivery', (SELECT id FROM categories WHERE key_field='v2_logistics')),
    ('v2_logistics_other', (SELECT id FROM categories WHERE key_field='v2_logistics')),
    ('v2_education_languages', (SELECT id FROM categories WHERE key_field='v2_education')),
    ('v2_education_music', (SELECT id FROM categories WHERE key_field='v2_education')),
    ('v2_education_sport', (SELECT id FROM categories WHERE key_field='v2_education')),
    ('v2_education_courses', (SELECT id FROM categories WHERE key_field='v2_education')),
    ('v2_events_hosts', (SELECT id FROM categories WHERE key_field='v2_events')),
    ('v2_events_decor', (SELECT id FROM categories WHERE key_field='v2_events')),
    ('v2_events_media', (SELECT id FROM categories WHERE key_field='v2_events')),
    ('v2_events_entertainment', (SELECT id FROM categories WHERE key_field='v2_events')),
    ('v2_events_rent', (SELECT id FROM categories WHERE key_field='v2_events')),
    ('v2_medical_support_care', (SELECT id FROM categories WHERE key_field='v2_medical_support')),
    ('v2_medical_support_assist', (SELECT id FROM categories WHERE key_field='v2_medical_support')),
    ('v2_medical_support_psych', (SELECT id FROM categories WHERE key_field='v2_medical_support')),
    ('v2_tourism_travel', (SELECT id FROM categories WHERE key_field='v2_tourism')),
    ('v2_tourism_rent', (SELECT id FROM categories WHERE key_field='v2_tourism')),
    ('v2_tourism_media', (SELECT id FROM categories WHERE key_field='v2_tourism')),
    ('v2_tourism_boats', (SELECT id FROM categories WHERE key_field='v2_tourism'))
    ON CONFLICT DO NOTHING;

    -- Level 3 (Climate)
    INSERT INTO categories (key_field, parent_id) VALUES
    ('v2_home_climate_gas_boilers', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
    ('v2_home_climate_boilers', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
    ('v2_home_climate_solar', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
    ('v2_home_climate_ac', (SELECT id FROM categories WHERE key_field='v2_home_climate'))
    ON CONFLICT DO NOTHING;

    -- Level 3/4 Services
    INSERT INTO categories (key_field, parent_id, short_key_field) VALUES
    ('v2_home_sanitary_install', (SELECT id FROM categories WHERE key_field='v2_home_sanitary'), 'v2_home_sanitary_install_short'),
    ('v2_home_sanitary_repair', (SELECT id FROM categories WHERE key_field='v2_home_sanitary'), 'v2_home_sanitary_repair_short'),
    ('v2_home_electrical_mount', (SELECT id FROM categories WHERE key_field='v2_home_electrical'), 'v2_home_electrical_mount_short'),
    ('v2_home_electrical_repair', (SELECT id FROM categories WHERE key_field='v2_home_electrical'), 'v2_home_electrical_repair_short'),
    ('v2_home_light_sockets_lights', (SELECT id FROM categories WHERE key_field='v2_home_light_sockets'), 'v2_home_light_sockets_lights_short'),
    ('v2_home_light_sockets_sockets', (SELECT id FROM categories WHERE key_field='v2_home_light_sockets'), 'v2_home_light_sockets_sockets_short'),
    ('v2_home_assembly_small_furniture', (SELECT id FROM categories WHERE key_field='v2_home_assembly_small'), 'v2_home_assembly_small_furniture_short'),
    ('v2_home_assembly_small_repair', (SELECT id FROM categories WHERE key_field='v2_home_assembly_small'), 'v2_home_assembly_small_repair_short'),
    ('v2_home_doors_windows_doors', (SELECT id FROM categories WHERE key_field='v2_home_doors_windows'), 'v2_home_doors_windows_doors_short'),
    ('v2_home_doors_windows_windows', (SELECT id FROM categories WHERE key_field='v2_home_doors_windows'), 'v2_home_doors_windows_windows_short'),
    ('v2_home_doors_windows_balcon', (SELECT id FROM categories WHERE key_field='v2_home_doors_windows'), 'v2_home_doors_windows_balcon_short'),
    ('v2_home_climate_gas_boilers_install', (SELECT id FROM categories WHERE key_field='v2_home_climate_gas_boilers'), 'v2_home_climate_gas_boilers_install_short'),
    ('v2_home_climate_gas_boilers_repair', (SELECT id FROM categories WHERE key_field='v2_home_climate_gas_boilers'), 'v2_home_climate_gas_boilers_repair_short'),
    ('v2_home_climate_boilers_install', (SELECT id FROM categories WHERE key_field='v2_home_climate_boilers'), 'v2_home_climate_boilers_install_short'),
    ('v2_home_climate_boilers_repair', (SELECT id FROM categories WHERE key_field='v2_home_climate_boilers'), 'v2_home_climate_boilers_repair_short'),
    ('v2_home_climate_solar_install', (SELECT id FROM categories WHERE key_field='v2_home_climate_solar'), 'v2_home_climate_solar_install_short'),
    ('v2_home_climate_solar_repair', (SELECT id FROM categories WHERE key_field='v2_home_climate_solar'), 'v2_home_climate_solar_repair_short'),
    ('v2_home_climate_ac_install', (SELECT id FROM categories WHERE key_field='v2_home_climate_ac'), 'v2_home_climate_ac_install_short'),
    ('v2_home_climate_ac_repair', (SELECT id FROM categories WHERE key_field='v2_home_climate_ac'), 'v2_home_climate_ac_repair_short'),
    ('v2_home_climate_ac_service', (SELECT id FROM categories WHERE key_field='v2_home_climate_ac'), 'v2_home_climate_ac_service_short'),
    ('v2_home_kitchen_stove', (SELECT id FROM categories WHERE key_field='v2_home_kitchen'), 'v2_home_kitchen_stove_short'),
    ('v2_home_kitchen_hood', (SELECT id FROM categories WHERE key_field='v2_home_kitchen'), 'v2_home_kitchen_hood_short'),
    ('v2_home_cleaning_basic', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_basic_short'),
    ('v2_home_cleaning_deep', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_deep_short'),
    ('v2_home_cleaning_after_renovation', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_after_renovation_short'),
    ('v2_home_cleaning_window', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_window_short'),
    ('v2_home_cleaning_furniture', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_furniture_short'),
    ('v2_home_cleaning_carpet', (SELECT id FROM categories WHERE key_field='v2_home_cleaning'), 'v2_home_cleaning_carpet_short'),
    ('v2_home_decoration_painting', (SELECT id FROM categories WHERE key_field='v2_home_decoration'), 'v2_home_decoration_painting_short'),
    ('v2_home_decoration_tiling', (SELECT id FROM categories WHERE key_field='v2_home_decoration'), 'v2_home_decoration_tiling_short'),
    ('v2_home_decoration_flooring', (SELECT id FROM categories WHERE key_field='v2_home_decoration'), 'v2_home_decoration_flooring_short'),
    ('v2_home_decoration_drywall', (SELECT id FROM categories WHERE key_field='v2_home_decoration'), 'v2_home_decoration_drywall_short'),
    ('v2_electronics_major_washing', (SELECT id FROM categories WHERE key_field='v2_electronics_major'), 'v2_electronics_major_washing_short'),
    ('v2_electronics_major_dishwashing', (SELECT id FROM categories WHERE key_field='v2_electronics_major'), 'v2_electronics_major_dishwashing_short'),
    ('v2_electronics_major_fridge', (SELECT id FROM categories WHERE key_field='v2_electronics_major'), 'v2_electronics_major_fridge_short'),
    ('v2_electronics_major_stove', (SELECT id FROM categories WHERE key_field='v2_electronics_major'), 'v2_electronics_major_stove_short'),
    ('v2_electronics_gadgets_tv', (SELECT id FROM categories WHERE key_field='v2_electronics_gadgets'), 'v2_electronics_gadgets_tv_short'),
    ('v2_electronics_gadgets_phone', (SELECT id FROM categories WHERE key_field='v2_electronics_gadgets'), 'v2_electronics_gadgets_phone_short'),
    ('v2_electronics_gadgets_laptop', (SELECT id FROM categories WHERE key_field='v2_electronics_gadgets'), 'v2_electronics_gadgets_laptop_short'),
    ('v2_electronics_gadgets_pc', (SELECT id FROM categories WHERE key_field='v2_electronics_gadgets'), 'v2_electronics_gadgets_pc_short'),
    ('v2_electronics_gadgets_small', (SELECT id FROM categories WHERE key_field='v2_electronics_gadgets'), 'v2_electronics_gadgets_small_short'),
    ('v2_electronics_internet_wifi', (SELECT id FROM categories WHERE key_field='v2_electronics_internet'), 'v2_electronics_internet_wifi_short'),
    ('v2_electronics_home_systems_cameras', (SELECT id FROM categories WHERE key_field='v2_electronics_home_systems'), 'v2_electronics_home_systems_cameras_short'),
    ('v2_electronics_home_systems_intercom', (SELECT id FROM categories WHERE key_field='v2_electronics_home_systems'), 'v2_electronics_home_systems_intercom_short'),
    ('v2_electronics_home_systems_smart', (SELECT id FROM categories WHERE key_field='v2_electronics_home_systems'), 'v2_electronics_home_systems_smart_short'),
    ('v2_auto_repair_common', (SELECT id FROM categories WHERE key_field='v2_auto_repair'), 'v2_auto_repair_common_short'),
    ('v2_auto_repair_diagnostics', (SELECT id FROM categories WHERE key_field='v2_auto_repair'), 'v2_auto_repair_diagnostics_short'),
    ('v2_auto_repair_electrician', (SELECT id FROM categories WHERE key_field='v2_auto_repair'), 'v2_auto_repair_electrician_short'),
    ('v2_auto_service_tires', (SELECT id FROM categories WHERE key_field='v2_auto_service'), 'v2_auto_service_tires_short'),
    ('v2_auto_service_wash', (SELECT id FROM categories WHERE key_field='v2_auto_service'), 'v2_auto_service_wash_short'),
    ('v2_auto_transport_rental', (SELECT id FROM categories WHERE key_field='v2_auto_transport'), 'v2_auto_transport_rental_short'),
    ('v2_auto_transport_driver', (SELECT id FROM categories WHERE key_field='v2_auto_transport'), 'v2_auto_transport_driver_short'),
    ('v2_auto_transport_taxi', (SELECT id FROM categories WHERE key_field='v2_auto_transport'), 'v2_auto_transport_taxi_short'),
    ('v2_auto_transport_tow', (SELECT id FROM categories WHERE key_field='v2_auto_transport'), 'v2_auto_transport_tow_short'),
    ('v2_beauty_hair_men', (SELECT id FROM categories WHERE key_field='v2_beauty_hair'), 'v2_beauty_hair_men_short'),
    ('v2_beauty_hair_women', (SELECT id FROM categories WHERE key_field='v2_beauty_hair'), 'v2_beauty_hair_women_short'),
    ('v2_beauty_hair_coloring', (SELECT id FROM categories WHERE key_field='v2_beauty_hair'), 'v2_beauty_hair_coloring_short'),
    ('v2_beauty_hair_barber', (SELECT id FROM categories WHERE key_field='v2_beauty_hair'), 'v2_beauty_hair_barber_short'),
    ('v2_beauty_nails_manicure', (SELECT id FROM categories WHERE key_field='v2_beauty_nails'), 'v2_beauty_nails_manicure_short'),
    ('v2_beauty_nails_pedicure', (SELECT id FROM categories WHERE key_field='v2_beauty_nails'), 'v2_beauty_nails_pedicure_short'),
    ('v2_beauty_nails_extension', (SELECT id FROM categories WHERE key_field='v2_beauty_nails'), 'v2_beauty_nails_extension_short'),
    ('v2_beauty_face_eyelashes', (SELECT id FROM categories WHERE key_field='v2_beauty_face'), 'v2_beauty_face_eyelashes_short'),
    ('v2_beauty_face_brows', (SELECT id FROM categories WHERE key_field='v2_beauty_face'), 'v2_beauty_face_brows_short'),
    ('v2_beauty_face_cosmetology', (SELECT id FROM categories WHERE key_field='v2_beauty_face'), 'v2_beauty_face_cosmetology_short'),
    ('v2_beauty_face_makeup', (SELECT id FROM categories WHERE key_field='v2_beauty_face'), 'v2_beauty_face_makeup_short'),
    ('v2_beauty_body_massage', (SELECT id FROM categories WHERE key_field='v2_beauty_body'), 'v2_beauty_body_massage_short'),
    ('v2_beauty_body_depilation', (SELECT id FROM categories WHERE key_field='v2_beauty_body'), 'v2_beauty_body_depilation_short'),
    ('v2_beauty_body_tattoo', (SELECT id FROM categories WHERE key_field='v2_beauty_body'), 'v2_beauty_body_tattoo_short'),
    ('v2_beauty_body_piercing', (SELECT id FROM categories WHERE key_field='v2_beauty_body'), 'v2_beauty_body_piercing_short'),
    ('v2_home_help_care_babysitter', (SELECT id FROM categories WHERE key_field='v2_home_help_care'), 'v2_home_help_care_babysitter_short'),
    ('v2_home_help_care_caregiver', (SELECT id FROM categories WHERE key_field='v2_home_help_care'), 'v2_home_help_care_caregiver_short'),
    ('v2_home_help_house_housekeeper', (SELECT id FROM categories WHERE key_field='v2_home_help_house'), 'v2_home_help_house_housekeeper_short'),
    ('v2_home_help_house_cook', (SELECT id FROM categories WHERE key_field='v2_home_help_house'), 'v2_home_help_house_cook_short'),
    ('v2_home_help_errands_grocery', (SELECT id FROM categories WHERE key_field='v2_home_help_errands'), 'v2_home_help_errands_grocery_short'),
    ('v2_home_help_errands_medicine', (SELECT id FROM categories WHERE key_field='v2_home_help_errands'), 'v2_home_help_errands_medicine_short'),
    ('v2_home_help_errands_pets', (SELECT id FROM categories WHERE key_field='v2_home_help_errands'), 'v2_home_help_errands_pets_short'),
    ('v2_logistics_moving_movers', (SELECT id FROM categories WHERE key_field='v2_logistics_moving'), 'v2_logistics_moving_movers_short'),
    ('v2_logistics_moving_apartment', (SELECT id FROM categories WHERE key_field='v2_logistics_moving'), 'v2_logistics_moving_apartment_short'),
    ('v2_logistics_delivery_courier', (SELECT id FROM categories WHERE key_field='v2_logistics_delivery'), 'v2_logistics_delivery_courier_short'),
    ('v2_logistics_other_junk', (SELECT id FROM categories WHERE key_field='v2_logistics_other'), 'v2_logistics_other_junk_short'),
    ('v2_logistics_other_storage', (SELECT id FROM categories WHERE key_field='v2_logistics_other'), 'v2_logistics_other_storage_short'),
    ('v2_education_languages_turkish', (SELECT id FROM categories WHERE key_field='v2_education_languages'), 'v2_education_languages_turkish_short'),
    ('v2_education_languages_other', (SELECT id FROM categories WHERE key_field='v2_education_languages'), 'v2_education_languages_other_short'),
    ('v2_education_tutor', (SELECT id FROM categories WHERE key_field='v2_education'), 'v2_education_tutor_short'),
    ('v2_education_music_guitar', (SELECT id FROM categories WHERE key_field='v2_education_music'), 'v2_education_music_guitar_short'),
    ('v2_education_music_piano', (SELECT id FROM categories WHERE key_field='v2_education_music'), 'v2_education_music_piano_short'),
    ('v2_education_music_vocal', (SELECT id FROM categories WHERE key_field='v2_education_music'), 'v2_education_music_vocal_short'),
    ('v2_education_music_other', (SELECT id FROM categories WHERE key_field='v2_education_music'), 'v2_education_music_other_short'),
    ('v2_education_sport_fitness', (SELECT id FROM categories WHERE key_field='v2_education_sport'), 'v2_education_sport_fitness_short'),
    ('v2_education_sport_yoga', (SELECT id FROM categories WHERE key_field='v2_education_sport'), 'v2_education_sport_yoga_short'),
    ('v2_education_sport_pilates', (SELECT id FROM categories WHERE key_field='v2_education_sport'), 'v2_education_sport_pilates_short'),
    ('v2_education_sport_swimming', (SELECT id FROM categories WHERE key_field='v2_education_sport'), 'v2_education_sport_swimming_short'),
    ('v2_education_sport_martial', (SELECT id FROM categories WHERE key_field='v2_education_sport'), 'v2_education_sport_martial_short'),
    ('v2_education_courses_it', (SELECT id FROM categories WHERE key_field='v2_education_courses'), 'v2_education_courses_it_short'),
    ('v2_education_courses_design', (SELECT id FROM categories WHERE key_field='v2_education_courses'), 'v2_education_courses_design_short'),
    ('v2_education_courses_driving', (SELECT id FROM categories WHERE key_field='v2_education_courses'), 'v2_education_courses_driving_short'),
    ('v2_education_courses_crafts', (SELECT id FROM categories WHERE key_field='v2_education_courses'), 'v2_education_courses_crafts_short'),
    ('v2_education_courses_other', (SELECT id FROM categories WHERE key_field='v2_education_courses'), 'v2_education_courses_other_short'),
    ('v2_events_hosts_tamada', (SELECT id FROM categories WHERE key_field='v2_events_hosts'), 'v2_events_hosts_tamada_short'),
    ('v2_events_hosts_planner', (SELECT id FROM categories WHERE key_field='v2_events_hosts'), 'v2_events_hosts_planner_short'),
    ('v2_events_decor_style', (SELECT id FROM categories WHERE key_field='v2_events_decor'), 'v2_events_decor_style_short'),
    ('v2_events_decor_catering', (SELECT id FROM categories WHERE key_field='v2_events_decor'), 'v2_events_decor_catering_short'),
    ('v2_events_media_photo', (SELECT id FROM categories WHERE key_field='v2_events_media'), 'v2_events_media_photo_short'),
    ('v2_events_media_video', (SELECT id FROM categories WHERE key_field='v2_events_media'), 'v2_events_media_video_short'),
    ('v2_events_entertainment_dj', (SELECT id FROM categories WHERE key_field='v2_events_entertainment'), 'v2_events_entertainment_dj_short'),
    ('v2_events_entertainment_animator', (SELECT id FROM categories WHERE key_field='v2_events_entertainment'), 'v2_events_entertainment_animator_short'),
    ('v2_events_rent_equip', (SELECT id FROM categories WHERE key_field='v2_events_rent'), 'v2_events_rent_equip_short'),
    ('v2_medical_support_care_nurse', (SELECT id FROM categories WHERE key_field='v2_medical_support_care'), 'v2_medical_support_care_nurse_short'),
    ('v2_medical_support_care_rehab', (SELECT id FROM categories WHERE key_field='v2_medical_support_care'), 'v2_medical_support_care_rehab_short'),
    ('v2_medical_support_care_massage', (SELECT id FROM categories WHERE key_field='v2_medical_support_care'), 'v2_medical_support_care_massage_short'),
    ('v2_medical_support_assist_consultant', (SELECT id FROM categories WHERE key_field='v2_medical_support_assist'), 'v2_medical_support_assist_consultant_short'),
    ('v2_medical_support_assist_hospital', (SELECT id FROM categories WHERE key_field='v2_medical_support_assist'), 'v2_medical_support_assist_hospital_short'),
    ('v2_medical_support_assist_birth', (SELECT id FROM categories WHERE key_field='v2_medical_support_assist'), 'v2_medical_support_assist_birth_short'),
    ('v2_medical_support_psych_doctor', (SELECT id FROM categories WHERE key_field='v2_medical_support_psych'), 'v2_medical_support_psych_doctor_short'),
    ('v2_tourism_travel_hiking', (SELECT id FROM categories WHERE key_field='v2_tourism_travel'), 'v2_tourism_travel_hiking_short'),
    ('v2_tourism_travel_guide', (SELECT id FROM categories WHERE key_field='v2_tourism_travel'), 'v2_tourism_travel_guide_short'),
    ('v2_tourism_travel_excursions', (SELECT id FROM categories WHERE key_field='v2_tourism_travel'), 'v2_tourism_travel_excursions_short'),
    ('v2_tourism_rent_sup', (SELECT id FROM categories WHERE key_field='v2_tourism_rent'), 'v2_tourism_rent_sup_short'),
    ('v2_tourism_rent_bicycle', (SELECT id FROM categories WHERE key_field='v2_tourism_rent'), 'v2_tourism_rent_bicycle_short'),
    ('v2_tourism_rent_scooter', (SELECT id FROM categories WHERE key_field='v2_tourism_rent'), 'v2_tourism_rent_scooter_short'),
    ('v2_tourism_rent_sports', (SELECT id FROM categories WHERE key_field='v2_tourism_rent'), 'v2_tourism_rent_sports_short'),
    ('v2_tourism_media_photo', (SELECT id FROM categories WHERE key_field='v2_tourism_media'), 'v2_tourism_media_photo_short'),
    ('v2_tourism_media_video', (SELECT id FROM categories WHERE key_field='v2_tourism_media'), 'v2_tourism_media_video_short'),
    ('v2_tourism_boats_trip', (SELECT id FROM categories WHERE key_field='v2_tourism_boats'), 'v2_tourism_boats_trip_short')
    ON CONFLICT DO NOTHING;

END $$;
