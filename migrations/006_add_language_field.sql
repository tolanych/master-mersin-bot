-- Add language field back to users table for language switching functionality
ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'ru' CHECK (language IN ('ru', 'tr', 'en'));

-- Create index for language queries
CREATE INDEX IF NOT EXISTS idx_users_language ON users(language);