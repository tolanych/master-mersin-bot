import asyncpg
import os
import logging
import datetime
import time
from typing import Optional, List, Dict, Any
from utils.phone_utils import normalize_phone, get_phone_search_variants

log = logging.getLogger(__name__)

class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        # Cache placeholder (initialized in init)
        self.cache = None

    async def connect(self):
        """Create connection pool"""
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(self.dsn)
                log.info("Connected to PostgreSQL")
            except Exception as e:
                log.error(f"Failed to connect to PostgreSQL: {e}")
                raise

    async def init(self):
        """Initialize DB and apply migrations"""
        await self.connect()
        await self.apply_migrations()
        from utils.cache import UserCache
        self.cache = UserCache()

    async def apply_migrations(self):
        """Apply init_pg.sql and other migrations tracking them in schema_migrations"""
        async with self.pool.acquire() as conn:
            # 1. Create migrations tracking table first
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version     INTEGER PRIMARY KEY,
                    applied_at  TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """)
            
            # 2. Get applied versions
            applied_versions = await conn.fetch("SELECT version FROM schema_migrations")
            applied_set = {row['version'] for row in applied_versions}
            
            # Migration 0: Initial Schema
            if 0 not in applied_set:
                migration_file = os.path.join(os.path.dirname(__file__), "migrations", "init_pg.sql")
                if os.path.exists(migration_file):
                    log.info("Applying init_pg.sql (initial schema)...")
                    with open(migration_file, "r", encoding="utf-8") as f:
                        sql = f.read()
                    try:
                        await conn.execute(sql)
                        await conn.execute("INSERT INTO schema_migrations (version) VALUES (0)")
                        log.info("✅ Applied migration 0 (init_pg.sql)")
                    except Exception as e:
                        log.error(f"❌ Failed to apply init_pg.sql: {e}")
            
            # Migration 1: Optimize Indexes
            if 1 not in applied_set:
                migration_file = os.path.join(os.path.dirname(__file__), "migrations", "001_optimize_indexes.sql")
                if os.path.exists(migration_file):
                    log.info("Applying 001_optimize_indexes.sql...")
                    with open(migration_file, "r", encoding="utf-8") as f:
                        sql = f.read()
                    try:
                        await conn.execute(sql)
                        await conn.execute("INSERT INTO schema_migrations (version) VALUES (1)")
                        log.info("✅ Applied migration 1 (optimize_indexes)")
                    except Exception as e:
                        log.error(f"❌ Failed to apply 001_optimize_indexes.sql: {e}")

            # Migration 2: Create Complaints Table
            if 2 not in applied_set:
                migration_file = os.path.join(os.path.dirname(__file__), "migrations", "002_create_complaints.sql")
                if os.path.exists(migration_file):
                    log.info("Applying 002_create_complaints.sql...")
                    with open(migration_file, "r", encoding="utf-8") as f:
                        sql = f.read()
                    try:
                        await conn.execute(sql)
                        await conn.execute("INSERT INTO schema_migrations (version) VALUES (2)")
                        log.info("✅ Applied migration 2 (create_complaints)")
                    except Exception as e:
                        log.error(f"❌ Failed to apply 002_create_complaints.sql: {e}")

    async def close(self):
        """Close DB connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # ===== Basic Helpers =====

    async def fetchrow(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetch(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetchval(self, query: str, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    def debug_info(self):
        # Async methods can't be easily called here if this is used synchronously for debugging
        # But we can return connection info
        info = {
            "dsn_masked": self.dsn.replace(self.dsn.split(":")[2].split("@")[0], "***") if "@" in self.dsn else "N/A",
            "pool_status": "Open" if self.pool else "Closed"
        }
        return info

    # ===== Users API =====
    async def get_user_by_tg_id(self, tg_id):
        # 1. Try Cache
        if self.cache:
            cached = self.cache.get(tg_id)
            if cached:
                return cached

        # 2. Cache Miss - Fetch from DB
        query = """
            SELECT u.id as user_id, u.telegram_id, u.username, u.language, u.is_master, u.is_client, 
                   m.id as master_id, m.status as master_status 
            FROM users u
            LEFT JOIN masters m ON u.id = m.user_id 
            WHERE u.telegram_id = $1 LIMIT 1
        """
        row = await self.fetchrow(query, tg_id)
        
        if row:
            user = dict(row)
            # Add compatibility fields
            user['id'] = user['user_id']
            if 'language' not in user or not user['language']:
                 user['language'] = 'ru'
            
            # Store in cache
            if self.cache:
                self.cache.set(tg_id, user)
            return user
        
        return None

    async def get_user(self, user_id):
        # Try to find in cache by user_id
        if self.cache:
            for tg_id, (data, timestamp) in self.cache.cache.items():
                if data.get('user_id') == user_id:
                    # Check TTL logic is in cache.get but accessing raw cache here
                    if time.time() - timestamp < self.cache.ttl:
                        return data
        
        # Determine telegram_id if possible
        row = await self.fetchrow('SELECT telegram_id FROM users WHERE id=$1', user_id)
        if row:
            return await self.get_user_by_tg_id(row['telegram_id'])
            
        return None

    async def create_user(self, tg_id, username=None, language='ru'):
        query = """
            INSERT INTO users(telegram_id, username, is_client, is_master, status, created_at) 
            VALUES ($1, $2, TRUE, FALSE, 'active', NOW())
            RETURNING id
        """
        return await self.fetchval(query, tg_id, username)

    async def get_or_create_user(self, tg_id, username=None):
        user = await self.get_user_by_tg_id(tg_id)
        if user:
            return user['user_id']
        return await self.create_user(tg_id, username)

    async def set_user_master(self, user_id: int, is_master: bool = True):
        await self.execute('UPDATE users SET is_master=$1 WHERE id=$2', is_master, user_id)
        # Invalidate cache
        if self.cache:
            keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
            for k in keys_to_del:
                self.cache.invalidate(k)

    async def update_user_status(self, user_id: int, status: str):
        await self.execute('UPDATE users SET status=$1 WHERE id=$2', status, user_id)
        if self.cache:
            keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
            for k in keys_to_del:
                self.cache.invalidate(k)

    async def update_user_language(self, user_id: int, language: str):
        await self.execute('UPDATE users SET language=$1 WHERE id=$2', language, user_id)
        if self.cache:
            keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
            for k in keys_to_del:
                self.cache.invalidate(k)

    # ===== Masters API =====
    async def get_master_by_user_id(self, user_id: int):
        # Optimization: Check UserCache first
        if self.cache:
            for tg_id, (data, timestamp) in self.cache.cache.items():
                if data.get('user_id') == user_id:
                    if not data.get('is_master'):
                        return None
                    break

        query = """
            SELECT m.*, u.telegram_id, u.username 
            FROM masters m 
            JOIN users u ON m.user_id = u.id 
            WHERE m.user_id=$1
        """
        row = await self.fetchrow(query, user_id)
        return dict(row) if row else None

    async def get_master_by_phone(self, phone: str):
        variants = get_phone_search_variants(phone)
        if not variants:
            return None
        
        # Postgres ANY($1) for IN clause with dynamic list
        query = "SELECT * FROM masters WHERE phone = ANY($1::text[])"
        row = await self.fetchrow(query, variants)
        return dict(row) if row else None

    async def create_master(self, user_id, name, phone, description, categories, districts, source, status='draft'):
        normalized_phone = normalize_phone(phone)
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Insert master
                master_id = await conn.fetchval("""
                    INSERT INTO masters (user_id, name, phone, description, status, source, created_at) 
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    RETURNING id
                """, user_id, name, normalized_phone, description, status, source)
                
                # Insert categories
                if categories:
                    # Using executemany for bulk insert could be faster but loop is fine for small count
                    for category_id in categories:
                        await conn.execute("INSERT INTO master_categories (master_id, category_id) VALUES ($1, $2)", master_id, category_id)
                
                # Insert districts
                if districts:
                    for district_id in districts:
                        await conn.execute("INSERT INTO master_districts (master_id, district_id) VALUES ($1, $2)", master_id, district_id)
                
                # Log status
                await conn.execute("""
                    INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, created_at) 
                    VALUES ($1, $2, NULL, $3, NOW())
                """, 'master', master_id, status)
                
                log.info(f"Successfully created master {master_id} for user {user_id}")
                return master_id

    async def link_master_to_user(self, master_id: int, user_id: int):
        old_status = await self.fetchval("SELECT status FROM masters WHERE id=$1", master_id)
        new_status = 'active_free'
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE masters SET user_id=$1, status=$2 WHERE id=$3", user_id, new_status, master_id)
                
                await conn.execute("""
                    INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, changed_by, created_at) 
                    VALUES ($1, $2, $3, $4, $5, NOW())
                """, 'master', master_id, old_status, new_status, user_id)

        # Invalidate cache
        if self.cache:
            keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
            for k in keys_to_del:
                self.cache.invalidate(k)

    async def update_master_profile(self, master_id, name, phone, description, categories, districts):
        normalized_phone = normalize_phone(phone)
        
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    UPDATE masters SET name=$1, phone=$2, description=$3 WHERE id=$4
                """, name, normalized_phone, description, master_id)
                
                # Update categories
                await conn.execute("DELETE FROM master_categories WHERE master_id=$1", master_id)
                for category_id in categories:
                    await conn.execute("INSERT INTO master_categories (master_id, category_id) VALUES ($1, $2)", master_id, category_id)
                
                # Update districts
                await conn.execute("DELETE FROM master_districts WHERE master_id=$1", master_id)
                for district_id in districts:
                    await conn.execute("INSERT INTO master_districts (master_id, district_id) VALUES ($1, $2)", master_id, district_id)
        return True

    async def update_master_status(self, master_id: int, status: str, changed_by: int = None):
        old_status = await self.fetchval("SELECT status FROM masters WHERE id=$1", master_id)
        if old_status:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute('UPDATE masters SET status=$1 WHERE id=$2', status, master_id)
                    await conn.execute("""
                        INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, changed_by, created_at) 
                        VALUES ($1, $2, $3, $4, $5, NOW())
                    """, 'master', master_id, old_status, status, changed_by)

    async def get_master_categories(self, master_id: int):
        rows = await self.fetch("""
            SELECT c.* FROM categories c 
            JOIN master_categories mc ON c.id = mc.category_id 
            WHERE mc.master_id=$1
        """, master_id)
        return [dict(r) for r in rows]

    async def get_master_districts(self, master_id: int):
        rows = await self.fetch("""
            SELECT d.* FROM districts d 
            JOIN master_districts md ON d.id = md.district_id 
            WHERE md.master_id=$1
        """, master_id)
        return [dict(r) for r in rows]

    async def get_category_by_key(self, category_key: str):
        row = await self.fetchrow("SELECT * FROM categories WHERE key_field=$1", category_key)
        return dict(row) if row else None

    async def get_category(self, category_id: int):
        row = await self.fetchrow("SELECT * FROM categories WHERE id=$1", category_id)
        return dict(row) if row else None

    async def get_district_by_key(self, district_key: str):
        row = await self.fetchrow("SELECT * FROM districts WHERE key_field=$1", district_key)
        return dict(row) if row else None

    # ===== Categories API =====
    async def get_categories(self, parent_id=None):
        if parent_id is None:
            query = """
                SELECT c.*, (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as child_count 
                FROM categories c 
                WHERE parent_id IS NULL 
                ORDER BY key_field
            """
            rows = await self.fetch(query)
        else:
            query = """
                SELECT c.*, (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as child_count 
                FROM categories c 
                WHERE parent_id=$1 
                ORDER BY key_field
            """
            rows = await self.fetch(query, parent_id)
        return [dict(r) for r in rows]

    async def get_all_categories(self):
        rows = await self.fetch("SELECT * FROM categories ORDER BY parent_id, key_field")
        return [dict(r) for r in rows]

    # ===== Districts API =====
    async def get_districts(self):
        rows = await self.fetch("SELECT * FROM districts ORDER BY key_field")
        return [dict(r) for r in rows]

    async def is_premium_master(self, master_id: int):
        row = await self.fetchrow("SELECT premium_until FROM masters WHERE id=$1", master_id)
        if row and row['premium_until']:
            # In PG, premium_until is datetime object
            return row['premium_until'] > datetime.datetime.utcnow()
        return False

    async def get_master(self, master_id: int):
        # Optimized query with aggregations to avoid N+1 problem
        # Note: We use array_agg to get related IDs/keys in a single query.
        # Ensure your postgres setup allows subqueries.
        query = """
            SELECT m.*, u.telegram_id, u.username,
                   (
                       SELECT array_agg(c.key_field)
                       FROM master_categories mc
                       JOIN categories c ON mc.category_id = c.id
                       WHERE mc.master_id = m.id
                   ) as categories,
                   (
                       SELECT array_agg(d.key_field)
                       FROM master_districts md
                       JOIN districts d ON md.district_id = d.id
                       WHERE md.master_id = m.id
                   ) as districts,
                   (
                        SELECT COUNT(*) FROM orders o WHERE o.master_id = m.id AND o.status = 'completed'
                   ) as completed_orders_count
            FROM masters m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.id = $1
        """
        row = await self.fetchrow(query, master_id)
        if not row:
            return None
        
        result = dict(row)
        
        # Handle None for array_agg if no rows
        if result['categories'] is None:
            result['categories'] = []
        if result['districts'] is None:
            result['districts'] = []

        if result.get('rating') is None:
            result['rating'] = 0.0
            
        result['completed_orders'] = result['completed_orders_count']
        del result['completed_orders_count']
        
        return result

    async def get_master_reviews(self, master_id: int):
        rows = await self.fetch("""
            SELECT * FROM orders WHERE master_id = $1 and status = 'completed'
        """, master_id)
        return [dict(r) for r in rows]

    async def create_order(self, client_id: int, master_id: int, category_id: int = None):
        return await self.fetchval("""
            INSERT INTO orders (client_id, master_id, category_id, status, created_at) 
            VALUES ($1, $2, $3, 'active', NOW())
            RETURNING id
        """, client_id, master_id, category_id)

    async def get_client_pending_order(self, client_id: int):
        # 24 hours ago
        # PostgreSQL supports interval syntax
        query = """
            SELECT o.*, m.name as master_name, m.phone as master_phone 
            FROM orders o 
            JOIN masters m ON o.master_id = m.id
            WHERE o.client_id = $1 
            AND o.status = 'active'
            AND o.created_at < (NOW() - INTERVAL '24 hours')
            ORDER BY o.created_at ASC
            LIMIT 1
        """
        row = await self.fetchrow(query, client_id)
        return dict(row) if row else None

    async def complete_order(self, order_id: int, rating: int = None, review: str = None, price: int = None):
        if rating is not None:
             await self.execute("""
                UPDATE orders SET status='completed', completed_at=NOW(), rating=$2, review_text=$3, price=$4 WHERE id=$1
            """, order_id, rating, review, price)
        else:
            await self.execute("""
                UPDATE orders SET status='completed', completed_at=NOW() WHERE id=$1
            """, order_id)

    async def search_masters(self, category_ids: list[int], district_ids: list[int], exclude_user_id: int = None):
        if not category_ids or not district_ids:
            return []

        # Build dynamic query
        # $1 = category_ids (array), $2 = district_ids (array)
        args = [category_ids, district_ids]
        
        exclude_clause = ""
        if exclude_user_id is not None:
            exclude_clause = "AND m.user_id != $3"
            args.append(exclude_user_id)
        
        sql = f"""
            SELECT m.*, u.username, u.telegram_id,
                   (SELECT COUNT(*) FROM orders o WHERE o.master_id = m.id AND o.status = 'completed') as completed_count
            FROM masters m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.status NOT IN ('blocked')
            AND EXISTS (SELECT 1 FROM master_categories mc WHERE mc.master_id = m.id AND mc.category_id = ANY($1::int[]))
            AND EXISTS (SELECT 1 FROM master_districts md WHERE md.master_id = m.id AND md.district_id = ANY($2::int[]))
            {exclude_clause}
            ORDER BY 
                CASE WHEN m.status = 'active_premium' THEN 0
                WHEN m.status = 'active_free' THEN 1
                else 2 END,
                m.rating DESC,
                completed_count DESC;
        """
        rows = await self.fetch(sql, *args)
        return [dict(r) for r in rows]

    async def update_master_rating(self, master_id: int):
        await self.execute("""
            UPDATE masters 
            SET rating = (SELECT AVG(rating) FROM orders WHERE master_id = $1 AND status = 'completed') 
            WHERE id = $1
        """, master_id)

    async def get_master_order_stats(self, master_id: int):
        row = await self.fetchrow("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as satisfied_clients,
                COUNT(rating) as rated_orders
            FROM orders 
            WHERE master_id = $1 AND status = 'completed'
        """, master_id)
        return dict(row) if row else {'total_orders': 0, 'satisfied_clients': 0, 'rated_orders': 0}

    async def create_concierge_request(self, user_id: int, categories: str, phone: str, name: str):
        return await self.fetchval("""
            INSERT INTO service_requests (user_id, categories, phone, name) VALUES ($1, $2, $3, $4) RETURNING id
        """, user_id, categories, phone, name)

    async def add_premium_request(self, master_id: int, user_id: int, status: str):
        return await self.fetchval("""
            INSERT INTO premium_requests (master_id, user_id, status) VALUES ($1, $2, $3) RETURNING id
        """, master_id, user_id, status)

    async def get_order(self, order_id: int):
        row = await self.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
        return dict(row) if row else None

    async def get_client_orders(self, client_id: int):
        rows = await self.fetch("""
            SELECT o.*, m.name as master_name, m.phone as master_phone, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = $1
            ORDER BY CASE WHEN o.status = 'active' THEN 1 ELSE 2 END ASC, o.created_at DESC
        """, client_id)
        return [dict(r) for r in rows]

    async def get_active_orders_count(self, client_id: int) -> int:
        return await self.fetchval("SELECT COUNT(*) FROM orders WHERE client_id = $1 AND status = 'active'", client_id)

    async def get_active_orders(self, client_id: int):
        rows = await self.fetch("""
            SELECT o.*, m.name as master_name, m.phone as master_phone, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = $1 AND o.status = 'active'
            ORDER BY o.created_at DESC
        """, client_id)
        return [dict(r) for r in rows]

    async def get_completed_orders(self, client_id: int, limit: int = 10, offset: int = 0):
        rows = await self.fetch("""
            SELECT o.*, m.name as master_name, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = $1 AND o.status = 'completed'
            ORDER BY o.created_at DESC
            LIMIT $2 OFFSET $3
        """, client_id, limit, offset)
        return [dict(r) for r in rows]

    async def get_completed_orders_count(self, client_id: int) -> int:
        return await self.fetchval("SELECT COUNT(*) FROM orders WHERE client_id = $1 AND status = 'completed'", client_id)

    # ===== Client Profiles API =====
    async def get_client_profile(self, user_id: int):
        row = await self.fetchrow('SELECT * FROM client_profiles WHERE user_id=$1', user_id)
        return dict(row) if row else None

    async def create_client_profile(self, user_id: int, phone: str = None, phone_verified: bool = False):
        normalized_phone = normalize_phone(phone) if phone else None
        return await self.fetchval("""
            INSERT INTO client_profiles (user_id, phone, phone_verified, created_at, updated_at) 
            VALUES ($1, $2, $3, NOW(), NOW())
            RETURNING user_id
        """, user_id, normalized_phone, phone_verified)

    async def update_client_phone(self, user_id: int, phone: str, phone_verified: bool = True):
        normalized_phone = normalize_phone(phone)
        result = await self.execute("""
            UPDATE client_profiles SET phone=$1, phone_verified=$2, updated_at=NOW() WHERE user_id=$3
        """, normalized_phone, phone_verified, user_id)
        # asyncpg execute returns "UPDATE N" string.
        return "UPDATE 0" not in result

    async def get_or_create_client_profile(self, user_id: int):
        profile = await self.get_client_profile(user_id)
        if profile:
            return profile
        await self.create_client_profile(user_id)
        return await self.get_client_profile(user_id)

    async def update_client_rating(self, user_id: int):
        avg_rating = await self.fetchval("""
            SELECT AVG(client_rating) FROM orders WHERE client_id = $1 AND client_rating IS NOT NULL
        """, user_id)
        if avg_rating is None:
            avg_rating = 5.0
        
        await self.execute("UPDATE client_profiles SET rating=$1, updated_at=NOW() WHERE user_id=$2", avg_rating, user_id)

    async def get_client_order_stats(self, user_id: int):
        row = await self.fetchrow("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) as cancelled
            FROM orders WHERE client_id = $1
        """, user_id)
        return {
            'completed': row['completed'] if row else 0,
            'cancelled': row['cancelled'] if row else 0
        }

    async def update_client_order_stats(self, user_id: int):
        stats = await self.get_client_order_stats(user_id)
        await self.execute("""
            UPDATE client_profiles SET total_completed=$1, total_cancelled=$2, updated_at=NOW() WHERE user_id=$3
        """, stats['completed'], stats['cancelled'], user_id)

    async def rate_client(self, order_id: int, rating: int):
        await self.execute("UPDATE orders SET client_rating=$1 WHERE id=$2", rating, order_id)
        client_id = await self.fetchval("SELECT client_id FROM orders WHERE id=$1", order_id)
        if client_id:
            await self.update_client_rating(client_id)

    async def create_complaint(self, user_id: int, master_id: int, text: str):
        return await self.fetchval("""
            INSERT INTO complaints (user_id, master_id, text, created_at) 
            VALUES ($1, $2, $3, NOW())
            RETURNING id
        """, user_id, master_id, text)

    async def get_client_reviews_for_masters(self, user_id: int):
        rows = await self.fetch("""
            SELECT o.*, m.name as master_name, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = $1 AND o.rating IS NOT NULL
            ORDER BY o.completed_at DESC
        """, user_id)
        return [dict(r) for r in rows]

    # ===== Reputation System API =====
    async def get_criteria(self, role_client: bool):
        rows = await self.fetch("SELECT * FROM reputation_criteria WHERE role_client=$1 ORDER BY group_key, id", role_client)
        return [dict(r) for r in rows]

    async def save_votes(self, from_client: bool, order_id: int, criterion_ids: list[int]):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM reputation_votes WHERE order_id=$1 AND from_client=$2", order_id, from_client)
                for cid in criterion_ids:
                    await conn.execute("INSERT INTO reputation_votes (from_client, order_id, criterion_id) VALUES ($1, $2, $3)", from_client, order_id, cid)

    async def get_user_reputation_stats(self, user_id: int = None, master_id: int = None):
        """
        Get reputation stats for a user (as master and as client).
        Supports three cases:
        1. Client (pass user_id)
        2. Master linked to user (pass user_id or both)
        3. Master not linked to user (pass master_id, user_id can be -1 or None)
        """
        # If master_id not provided, try to find it via user_id
        if master_id is None and user_id is not None and user_id != -1:
            master = await self.get_master_by_user_id(user_id)
            if master:
                master_id = master['id']

        master_stats = {}
        master_total = 0
        
        all_master_criteria = await self.get_criteria(role_client=True)
        for crit in all_master_criteria:
            master_stats[crit['code_key']] = {'percent': 0.0, 'count': 0}

        if master_id is not None and master_id != -1:
            master_total = await self.fetchval("""
                SELECT COUNT(DISTINCT order_id) 
                FROM reputation_votes rv
                JOIN orders o ON rv.order_id = o.id
                WHERE o.master_id = $1 AND rv.from_client = TRUE
            """, master_id)
            
            if master_total > 0:
                rows = await self.fetch("""
                    SELECT rc.code_key, COUNT(rv.id) as count
                    FROM reputation_criteria rc
                    JOIN reputation_votes rv ON rc.id = rv.criterion_id
                    JOIN orders o ON rv.order_id = o.id
                    WHERE o.master_id = $1 AND rv.from_client = TRUE
                    GROUP BY rc.id, rc.code_key
                """, master_id)
                for row in rows:
                    master_stats[row['code_key']] = {
                        'percent': round((row['count'] / master_total) * 100, 1),
                        'count': row['count']
                    }

        client_total = 0
        client_stats = {}
        all_client_criteria = await self.get_criteria(role_client=False)
        for crit in all_client_criteria:
            client_stats[crit['code_key']] = {'percent': 0.0, 'count': 0}

        if user_id is not None and user_id != -1:
            client_total = await self.fetchval("""
                SELECT COUNT(DISTINCT order_id) 
                FROM reputation_votes rv
                JOIN orders o ON rv.order_id = o.id
                WHERE o.client_id = $1 AND rv.from_client = FALSE
            """, user_id)
            
            if client_total > 0:
                rows = await self.fetch("""
                    SELECT rc.code_key, COUNT(rv.id) as count
                    FROM reputation_criteria rc
                    JOIN reputation_votes rv ON rc.id = rv.criterion_id
                    JOIN orders o ON rv.order_id = o.id
                    WHERE o.client_id = $1 AND rv.from_client = FALSE
                    GROUP BY rc.id, rc.code_key
                """, user_id)
                for row in rows:
                    client_stats[row['code_key']] = {
                        'percent': round((row['count'] / client_total) * 100, 1),
                        'count': row['count']
                    }
        
        return {
            'as_master': {
                'total': master_total,
                'stats': master_stats
            },
            'as_client': {
                'total': client_total,
                'stats': client_stats
            }
        }
