-- ===== Migration 009: Client Profiles =====
-- Add client_rating and client_feedback to orders (master rates client after order)
-- Create client_profiles table

-- Add new columns to orders table
ALTER TABLE orders ADD COLUMN client_rating INTEGER;

-- Create client_profiles table
CREATE TABLE IF NOT EXISTS client_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    about TEXT,
    phone TEXT,
    phone_verified BOOLEAN DEFAULT 0,
    rating REAL DEFAULT 5.0,
    total_completed INTEGER DEFAULT 0,
    total_cancelled INTEGER DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookup by user_id
CREATE INDEX IF NOT EXISTS idx_client_profiles_user_id ON client_profiles(user_id);
