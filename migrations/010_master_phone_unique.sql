-- Migration to make master phone unique
CREATE UNIQUE INDEX IF NOT EXISTS idx_masters_phone ON masters(phone);
