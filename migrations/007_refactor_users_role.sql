-- Migration to replace role string with flags
-- Up
ALTER TABLE users ADD COLUMN is_client BOOLEAN DEFAULT 1;
ALTER TABLE users ADD COLUMN is_master BOOLEAN DEFAULT 0;
