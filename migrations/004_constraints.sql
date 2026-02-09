
-- status constraints (soft via CHECK)
CREATE TABLE IF NOT EXISTS _orders_tmp(
  id INTEGER PRIMARY KEY,
  service_request_id INTEGER,
  master_type TEXT,
  master_id INTEGER,
  status TEXT CHECK(status IN ('assigned','accepted','done','cancelled')),
  created_at TEXT
);
