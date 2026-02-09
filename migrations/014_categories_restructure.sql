BEGIN TRANSACTION;

-- Create a temporary table to store mapping of old keys to new keys
CREATE TEMP TABLE category_mapping (
    old_key TEXT,
    new_key TEXT
);

INSERT INTO category_mapping (old_key, new_key) VALUES
('plumbing_install', 'v2_home_sanitary_install'),
('plumbing_repair', 'v2_home_sanitary_repair'),
('electrical_install', 'v2_home_electrical_mount'),
('electrical_repair', 'v2_home_electrical_repair'),
('lighting_install', 'v2_home_light_sockets_lights'),
('socket_install', 'v2_home_light_sockets_sockets'),
('furniture_assembly', 'v2_home_assembly_small_furniture'),
('handyman_small_repair', 'v2_home_assembly_small_repair'),
('doors_install', 'v2_home_doors_windows_doors'),
('windows_repair', 'v2_home_doors_windows_windows'),
('balcon', 'v2_home_doors_windows_balcon'),
('boiler_install', 'v2_home_climate_gas_boilers_install'),
('boiler_repair', 'v2_home_climate_gas_boilers_repair'),
('water_heater_install', 'v2_home_climate_boilers_install'),
('water_heater_repair', 'v2_home_climate_boilers_repair'),
('solar_install', 'v2_home_climate_solar_install'),
('solar_repair', 'v2_home_climate_solar_repair'),
('ac_install', 'v2_home_climate_ac_install'),
('ac_repair', 'v2_home_climate_ac_repair'),
('ac_service', 'v2_home_climate_ac_service'),
('kitchen_appliance_install', 'v2_home_kitchen_stove'),
('hood_install', 'v2_home_kitchen_hood'),
('cleaning_basic', 'v2_home_cleaning_basic'),
('cleaning_deep', 'v2_home_cleaning_deep'),
('cleaning_after_renovation', 'v2_home_cleaning_after_renovation'),
('window_cleaning', 'v2_home_cleaning_window'),
('furniture_dry_cleaning', 'v2_home_cleaning_furniture'),
('carpet_dry_cleaning', 'v2_home_cleaning_carpet'),
('painting', 'v2_home_decoration_painting'),
('tiling', 'v2_home_decoration_tiling'),
('flooring', 'v2_home_decoration_flooring'),
('drywall', 'v2_home_decoration_drywall'),
('washing_machine_repair', 'v2_electronics_major_washing'),
('dishwasher_repair', 'v2_electronics_major_dishwashing'),
('fridge_repair', 'v2_electronics_major_fridge'),
('oven_repair', 'v2_electronics_major_stove'),
('tv_repair', 'v2_electronics_gadgets_tv'),
('phone_repair', 'v2_electronics_gadgets_phone'),
('laptop_repair', 'v2_electronics_gadgets_laptop'),
('pc_repair', 'v2_electronics_gadgets_pc'),
('small_electronics_repair', 'v2_electronics_gadgets_small'),
('wifi_setup', 'v2_electronics_internet_wifi'),
('cctv_install', 'v2_electronics_home_systems_cameras'),
('intercom_install', 'v2_electronics_home_systems_intercom'),
('smart_home_install', 'v2_electronics_home_systems_smart'),
('car_repair', 'v2_auto_repair_common'),
('car_diagnostics', 'v2_auto_repair_diagnostics'),
('auto_electrician', 'v2_auto_repair_electrician'),
('tire_service', 'v2_auto_service_tires'),
('car_wash_detailing', 'v2_auto_service_wash'),
('car_rental', 'v2_auto_transport_rental'),
('driver_service', 'v2_auto_transport_driver'),
('taxi_transfer', 'v2_auto_transport_taxi'),
('tow_truck', 'v2_auto_transport_tow');

-- Level 1: Groups
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
('v2_tourism', NULL);

-- Level 2: Subgroups (Using SELECT for parent_id)
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
('v2_tourism_boats', (SELECT id FROM categories WHERE key_field='v2_tourism'));

-- Level 3: Climate Sub-Subgroups
INSERT INTO categories (key_field, parent_id) VALUES
('v2_home_climate_gas_boilers', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
('v2_home_climate_boilers', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
('v2_home_climate_solar', (SELECT id FROM categories WHERE key_field='v2_home_climate')),
('v2_home_climate_ac', (SELECT id FROM categories WHERE key_field='v2_home_climate'));

-- Level 3/4: Services
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
('v2_tourism_boats_trip', (SELECT id FROM categories WHERE key_field='v2_tourism_boats'), 'v2_tourism_boats_trip_short');

-- 3. Migrate master_categories links
INSERT INTO master_categories (master_id, category_id)
SELECT mc.master_id, c_new.id
FROM master_categories mc
JOIN categories c_old ON mc.category_id = c_old.id
JOIN category_mapping m ON c_old.key_field = m.old_key
JOIN categories c_new ON m.new_key = c_new.key_field;

COMMIT;

-- Drop temp table
DROP TABLE category_mapping;
