-- Optimization: Add missing indexes for foreign keys and frequent query filters

-- Categories: Key lookup is frequent, but parent_id is used for traversing
CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);

-- Orders: Filtering by master, status, and client is very frequent
CREATE INDEX IF NOT EXISTS idx_orders_master_id ON orders(master_id);
-- idx_orders_client_status already exists in init_pg.sql
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Reputation: Votes are aggregated by order and criterion
CREATE INDEX IF NOT EXISTS idx_reputation_votes_order_id ON reputation_votes(order_id);
CREATE INDEX IF NOT EXISTS idx_reputation_votes_criterion_id ON reputation_votes(criterion_id);

-- Many-to-Many Join Tables: PK covers (id1, id2), but reverse lookup needs index
-- master_categories: PK is (master_id, category_id). Finding masters by category needs index on category_id
CREATE INDEX IF NOT EXISTS idx_master_categories_category_id ON master_categories(category_id);

-- master_districts: PK is (master_id, district_id). Finding masters by district needs index on district_id
CREATE INDEX IF NOT EXISTS idx_master_districts_district_id ON master_districts(district_id);
