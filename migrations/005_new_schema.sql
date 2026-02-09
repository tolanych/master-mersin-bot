-- New schema migration - restructure according to database.md
-- This migration will recreate the entire schema with the new business relations

-- Users table - all Telegram users
CREATE TABLE users (
    id              INTEGER PRIMARY KEY,
    telegram_id     BIGINT UNIQUE NOT NULL,
    username        TEXT,
    status          TEXT CHECK (status IN ('active','blocked')) NOT NULL DEFAULT 'active',
    created_at      DATETIME NOT NULL
);

-- Masters table - only created when user clicks "Become a master"
CREATE TABLE masters (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    name            TEXT NOT NULL,
    phone           TEXT NOT NULL,
    description           TEXT NOT NULL,
    source          TEXT CHECK (
        source IN (
            'myself',
            'user'
        )
    ) NOT NULL,
    status          TEXT CHECK (
        status IN (
            'draft',
            'pending',
            'active_free',
            'active_premium',
            'blocked'
        )
    ) NOT NULL,
    premium_until   DATETIME,
    created_at      DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES users(id),
    master_id INTEGER NOT NULL REFERENCES masters(id),
    category_id INTEGER, -- Optional: which category was this order for
    status TEXT NOT NULL DEFAULT 'active', -- active, completed, cancelled
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME,
    rating INTEGER,
    review_text TEXT,
    price INTEGER
);

-- Index for quick lookup of active orders
CREATE INDEX IF NOT EXISTS idx_orders_client_status ON orders(client_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at);

-- Districts table using key fields
CREATE TABLE districts (
    id          INTEGER PRIMARY KEY,
    key_field   TEXT UNIQUE NOT NULL
);

-- Insert districts
INSERT INTO districts (id, key_field) VALUES 
(1, 'tashucu'),
(2, 'silifke'), 
(3, 'tece'),
(4, 'erdemli'),
(5, 'mezitli'),
(6, 'yenisehir'),
(7, 'akdeniz'),
(8, 'toroslar'),
(9, 'mut'),
(10, 'aydincik');


CREATE TABLE categories (
    id          INTEGER PRIMARY KEY,
    parent_id   INTEGER,
    key_field   TEXT UNIQUE NOT NULL,
    short_key_field TEXT
);

-- Master categories - many-to-many relationship
CREATE TABLE master_categories (
    master_id      INTEGER REFERENCES masters(id),
    category_id    INTEGER REFERENCES categories(id),
    PRIMARY KEY (master_id, category_id)
);

-- Master districts - many-to-many relationship
CREATE TABLE master_districts (
    master_id      INTEGER REFERENCES masters(id),
    district_id    INTEGER REFERENCES districts(id),
    PRIMARY KEY (master_id, district_id)
);

-- Premium payments
CREATE TABLE premium_payments (
    id              INTEGER PRIMARY KEY,
    master_id       INTEGER NOT NULL REFERENCES masters(id),
    amount          INTEGER NOT NULL,
    status          TEXT CHECK (
        status IN ('pending','confirmed','rejected')
    ) NOT NULL,
    admin_id        INTEGER REFERENCES users(id),
    premium_until   DATETIME,
    created_at      DATETIME NOT NULL,
    confirmed_at    DATETIME
);

-- Status logs for debugging and conflict resolution
CREATE TABLE status_logs (
    id          INTEGER PRIMARY KEY,
    entity_type TEXT CHECK (entity_type IN ('master','request')),
    entity_id   INTEGER NOT NULL,
    old_status  TEXT,
    new_status  TEXT NOT NULL,
    changed_by  INTEGER REFERENCES users(id),
    created_at  DATETIME NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_masters_user_id ON masters(user_id);
CREATE INDEX idx_masters_status ON masters(status);
CREATE INDEX idx_premium_payments_master_id ON premium_payments(master_id);
CREATE INDEX idx_status_logs_entity ON status_logs(entity_type, entity_id);