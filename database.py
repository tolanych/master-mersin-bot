import sqlite3, os, logging, datetime, time
from utils.phone_utils import normalize_phone, get_phone_search_variants
log = logging.getLogger(__name__)

RETRIES = 3

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._pragmas()
        return self.conn

    def _pragmas(self):
        self.conn.execute("PRAGMA foreign_keys=ON;")
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA busy_timeout=5000;")

    def init(self):
        self.connect()
        self.apply_migrations()
        from utils.cache import UserCache
        self.cache = UserCache()

    def apply_migrations(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at DATETIME NOT NULL)")
        applied = {row[0] for row in cur.execute("SELECT version FROM schema_migrations")}
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        for fname in sorted(os.listdir(migrations_dir)):
            if not fname.endswith(".sql"): continue
            version = int(fname.split("_")[0])
            if version in applied: continue
            with open(os.path.join(migrations_dir, fname), "r", encoding="utf-8") as f:
                sql = f.read()
            cur.executescript(sql)
            print(f"Applied migration {version}")
            print(sql)
            cur.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                        (version, datetime.datetime.utcnow().isoformat()))
            self.conn.commit()
            applied.add(version)

    def _execute(self, fn):
        last = None
        for i in range(RETRIES):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                last = e
                if "locked" in str(e).lower():
                    time.sleep(0.1 * (i+1))
                    continue
                raise
        raise last

    def execute(self, sql, params=()):
        return self._execute(lambda: self.conn.execute(sql, params))

    def executescript(self, sql):
        return self._execute(lambda: self.conn.executescript(sql))

    def debug_info(self):
        cur = self.conn.cursor()
        info = {}
        info["DB_PATH_env"] = os.getenv("DB_PATH")
        info["db_path"] = self.db_path
        info["realpath"] = os.path.realpath(self.db_path)
        info["cwd"] = os.getcwd()
        info["tables"] = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        info["schema_version"] = max([r[0] for r in cur.execute("SELECT version FROM schema_migrations")], default=0)
        info["pragmas"] = {
            "foreign_keys": cur.execute("PRAGMA foreign_keys").fetchone()[0],
            "journal_mode": cur.execute("PRAGMA journal_mode").fetchone()[0],
            "user_version": cur.execute("PRAGMA user_version").fetchone()[0],
        }
        info["counts"] = {}
        for t in ["users","masters","categories","districts","premium_payments","status_logs"]:
            try:
                info["counts"][t] = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            except Exception:
                info["counts"][t] = "n/a"
        return info

    async def close(self):
        """Close DB connection (async-friendly for aiogram/FastAPI lifecycles)."""
        try:
            if self.conn is not None:
                self.conn.close()
        finally:
            self.conn = None

    # ===== Users API =====
    async def get_user_by_tg_id(self, tg_id):
        # 1. Try Cache
        cached = self.cache.get(tg_id)
        if cached:
            print(f"Cache hit {tg_id} {cached}")
            return cached

        print(f"Cache pass {tg_id}")

        # 2. Cache Miss - Fetch from DB
        cur = self.conn.execute('''
            SELECT u.id as user_id, u.telegram_id, u.username, u.language, u.is_master, u.is_client, 
                   m.id as master_id, m.status as master_status 
            FROM users u
            LEFT JOIN masters m ON u.id = m.user_id 
            WHERE u.telegram_id = ? LIMIT 1
        ''', (tg_id,))
        row = cur.fetchone()
        
        if row:
            user = dict(row)
            # Add compatibility fields
            user['id'] = user['user_id']
            if 'language' not in user or not user['language']:
                 user['language'] = 'ru'
            
            # Store in cache
            self.cache.set(tg_id, user)
            return user
        
        return None

    async def get_user(self, user_id):
        # Try to find in cache by user_id
        for tg_id, (data, timestamp) in self.cache.cache.items():
            if data.get('user_id') == user_id:
                # Check TTL
                if time.time() - timestamp < self.cache.ttl:
                    return data
        
        # Determine telegram_id if possible to cache properly
        cur = self.conn.execute('SELECT telegram_id FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if row:
            return await self.get_user_by_tg_id(row['telegram_id'])
            
        return None

    async def create_user(self, tg_id, username=None, language='ru'):
        cur = self.conn.execute(
            'INSERT INTO users(telegram_id, username, is_client, is_master, status, created_at) VALUES (?,?,?,?,?,?)', 
            (tg_id, username, 1, 0, 'active', datetime.datetime.utcnow().isoformat())
        )
        self.conn.commit()
        # Invalidate/Update Cache? 
        # Actually create_user implies a new user, so we should cache it if we want.
        # But for now, next get calls will cache it.
        return cur.lastrowid

    async def get_or_create_user(self, tg_id, username=None):
        user = await self.get_user_by_tg_id(tg_id)
        if user:
            return user['user_id']
        return await self.create_user(tg_id, username)

    async def set_user_master(self, user_id: int, is_master: bool = True):
        self.conn.execute('UPDATE users SET is_master=? WHERE id=?', (1 if is_master else 0, user_id))
        self.conn.commit()
        # Invalidate cache for this user
        # We need to find the tg_id to invalidate
        user = await self.get_user(user_id)
        if user and 'telegram_id' in user: # wait, 'telegram_id' might not be in the Flattened query result?
             # 'telegram_id' is NOT in the requested flat query. 
             # I need to ensure it IS there for this purpose, OR search cache.
             # I'll rely on cache search in `get_user` or `invalidate` helper.
             pass
        # simpler: invalidate entire cache or just search-and-delete
        keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
        for k in keys_to_del:
            self.cache.invalidate(k)

    async def update_user_status(self, user_id: int, status: str):
        self.conn.execute('UPDATE users SET status=? WHERE id=?', (status, user_id))
        self.conn.commit()
        keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
        for k in keys_to_del:
            self.cache.invalidate(k)

    async def update_user_language(self, user_id: int, language: str):
        """Update user's language preference"""
        cur = self.conn.execute('UPDATE users SET language=? WHERE id=?', (language, user_id))
        self.conn.commit()
        keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
        for k in keys_to_del:
             # Option: Update the cache instead of invalidating? 
             # Cache invalidation is safer.
            self.cache.invalidate(k)

    # ===== Masters API =====
    async def get_master_by_user_id(self, user_id: int):
        # Optimization: Check UserCache first
        for tg_id, (data, timestamp) in self.cache.cache.items():
            if data.get('user_id') == user_id:
                if not data.get('is_master'):
                    return None
                # If is_master is True, we proceed to fetch full details
                # We could potentially cache master details too, but respecting scope:
                break

        cur = self.conn.execute(
            "SELECT m.*, u.telegram_id, u.username FROM masters m JOIN users u ON m.user_id = u.id WHERE m.user_id=?",
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

    async def get_master_by_phone(self, phone: str):
        variants = get_phone_search_variants(phone)
        if not variants:
            return None
        
        placeholders = ','.join(['?'] * len(variants))
        sql = f"SELECT * FROM masters WHERE phone IN ({placeholders})"
        cur = self.conn.execute(sql, tuple(variants))
        row = cur.fetchone()
        return dict(row) if row else None

    async def create_master(self, user_id, name, phone, description, categories, districts, source, status='draft'):
        """Create a master record with associated categories and districts.
        
        Args:
            user_id: ID of the user (or -1 for guest/unlinked)
            name: Master's name
            phone: Master's phone
            description: Profile description
            categories: List of category IDs
            districts: List of district IDs
            source: 'myself' or 'user'
            status: Initial status (default 'draft')
        """
        cur = self.conn.cursor()
        
        normalized_phone = normalize_phone(phone)
        
        try:
            # Insert into masters table
            cur.execute(
                "INSERT INTO masters (user_id, name, phone, description, status, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, name, normalized_phone, description, status, source, datetime.datetime.utcnow().isoformat())
            )
            master_id = cur.lastrowid
            
            if not master_id:
                raise sqlite3.Error("Failed to retrieve lastrowid after master insertion")
                
            # Insert categories
            for category_id in categories:
                cur.execute(
                    "INSERT INTO master_categories (master_id, category_id) VALUES (?, ?)",
                    (master_id, category_id)
                )
            
            # Insert districts
            for district_id in districts:
                cur.execute(
                    "INSERT INTO master_districts (master_id, district_id) VALUES (?, ?)",
                    (master_id, district_id)
                )
            
            # Log status change
            cur.execute(
                "INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, created_at) VALUES (?, ?, ?, ?, ?)",
                ('master', master_id, None, status, datetime.datetime.utcnow().isoformat())
            )
            
            self.conn.commit()
            log.info(f"Successfully created master {master_id} for user {user_id}")
            return master_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            log.error(f"Database error during create_master: {e}")
            raise
        except Exception as e:
            self.conn.rollback()
            log.error(f"Unexpected error during create_master: {e}")
            raise

    async def link_master_to_user(self, master_id: int, user_id: int):
        """Link an unverified master (user_id=-1) to a real user
        Automatically sets status to 'active_free' upon linkage.
        """
        cur = self.conn.execute("SELECT status FROM masters WHERE id=?", (master_id,))
        row = cur.fetchone()
        old_status = row[0] if row else None
        
        new_status = 'active_free'
        self.conn.execute("UPDATE masters SET user_id=?, status=? WHERE id=?", (user_id, new_status, master_id))
        
        # Log status change
        self.conn.execute(
            "INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ('master', master_id, old_status, new_status, user_id, datetime.datetime.utcnow().isoformat())
        )
        self.conn.commit()

        # Invalidate cache for this user to reflect new master status and ID
        keys_to_del = [k for k, (v, _) in self.cache.cache.items() if v.get('user_id') == user_id]
        for k in keys_to_del:
            self.cache.invalidate(k)

    async def update_master_profile(self, master_id, name, phone, description, categories, districts):
        cur = self.conn.cursor()
        
        normalized_phone = normalize_phone(phone)
        
        # Update masters table
        cur.execute(
            "UPDATE masters SET name=?, phone=?, description=? WHERE id=?",
            (name, normalized_phone, description, master_id)
        )
        
        # Update categories: delete all and re-insert
        cur.execute("DELETE FROM master_categories WHERE master_id=?", (master_id,))
        for category_id in categories:
            cur.execute(
                "INSERT INTO master_categories (master_id, category_id) VALUES (?, ?)",
                (master_id, category_id)
            )
        
        # Update districts: delete all and re-insert
        cur.execute("DELETE FROM master_districts WHERE master_id=?", (master_id,))
        for district_id in districts:
            cur.execute(
                "INSERT INTO master_districts (master_id, district_id) VALUES (?, ?)",
                (master_id, district_id)
            )
        
        self.conn.commit()
        return True

    async def update_master_status(self, master_id: int, status: str, changed_by: int = None):
        cur = self.conn.execute("SELECT status FROM masters WHERE id=?", (master_id,))
        current_status = cur.fetchone()
        if current_status:
            old_status = current_status[0]
            self.conn.execute('UPDATE masters SET status=? WHERE id=?', (status, master_id))
            
            # Log status change
            self.conn.execute(
                "INSERT INTO status_logs (entity_type, entity_id, old_status, new_status, changed_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                ('master', master_id, old_status, status, changed_by, datetime.datetime.utcnow().isoformat())
            )
            
            self.conn.commit()

    async def get_master_categories(self, master_id: int):
        cur = self.conn.execute(
            "SELECT c.* FROM categories c JOIN master_categories mc ON c.id = mc.category_id WHERE mc.master_id=?",
            (master_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    async def get_master_districts(self, master_id: int):
        cur = self.conn.execute(
            "SELECT d.* FROM districts d JOIN master_districts md ON d.id = md.district_id WHERE md.master_id=?",
            (master_id,)
        )
        return [dict(r) for r in cur.fetchall()]

    async def get_category_by_key(self, category_key: str):
        cur = self.conn.execute("SELECT * FROM categories WHERE key_field=?", (category_key,))
        row = cur.fetchone()
        return dict(row) if row else None

    async def get_category(self, category_id: int):
        cur = self.conn.execute("SELECT * FROM categories WHERE id=?", (category_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    async def get_district_by_key(self, district_key: str):
        cur = self.conn.execute("SELECT * FROM districts WHERE key_field=?", (district_key,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ===== Categories API =====
    async def get_categories(self, parent_id=None):
        if parent_id is None:
            cur = self.conn.execute("""
                SELECT c.*, (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as child_count 
                FROM categories c 
                WHERE parent_id IS NULL 
                ORDER BY key_field
            """)
        else:
            cur = self.conn.execute("""
                SELECT c.*, (SELECT COUNT(*) FROM categories WHERE parent_id = c.id) as child_count 
                FROM categories c 
                WHERE parent_id=? 
                ORDER BY key_field
            """, (parent_id,))
        return [dict(r) for r in cur.fetchall()]

    async def get_all_categories(self):
        cur = self.conn.execute("SELECT * FROM categories ORDER BY parent_id, key_field")
        return [dict(r) for r in cur.fetchall()]

    # ===== Districts API =====
    async def get_districts(self):
        cur = self.conn.execute("SELECT * FROM districts ORDER BY key_field")
        return [dict(r) for r in cur.fetchall()]

    async def is_premium_master(self, master_id: int):
        cur = self.conn.execute(
            "SELECT premium_until FROM masters WHERE id=?",
            (master_id,)
        )
        row = cur.fetchone()
        if row and row['premium_until']:
            return datetime.datetime.fromisoformat(row['premium_until']) > datetime.datetime.utcnow()
        return False

    async def get_master(self, master_id: int):
        """Legacy method - get master by ID with additional fields"""
        cur = self.conn.execute("""
            SELECT m.*, u.telegram_id, u.username
            FROM masters m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.id = ?
        """, (master_id,))
        master = cur.fetchone()
        if not master:
            return None
        
        result = dict(master)
        
        # Add categories (now using key fields)
        categories = await self.get_master_categories(master_id)
        result['categories'] = [c['key_field'] for c in categories]
        
        # Add districts (now using key fields)
        districts = await self.get_master_districts(master_id)
        result['districts'] = [d['key_field'] for d in districts]
        
        # Add legacy fields for compatibility
        if result.get('rating') is None:
            result['rating'] = 0.0
        result['completed_orders'] = 0  # TODO: Calculate from orders table
        
        return result

    async def get_master_reviews(self, master_id: int):
        """reviews table"""
        cur = self.conn.execute("""
            SELECT *
            FROM orders
            WHERE master_id = ? and status = 'completed'
        """, (master_id,))

        result = cur.fetchall()
        return result

    async def create_order(self, client_id: int, master_id: int, category_id: int = None):
        """Create a new order"""
        cur = self.conn.execute(
            "INSERT INTO orders (client_id, master_id, category_id, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (client_id, master_id, category_id, 'active', datetime.datetime.utcnow().isoformat())
        )
        self.conn.commit()
        return cur.lastrowid

    async def get_client_pending_order(self, client_id: int):
        """Check if client has any active orders older than 24 hours"""
        # 24 hours ago
        threshold = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat()
        
        cur = self.conn.execute("""
            SELECT o.*, m.name as master_name, m.phone as master_phone 
            FROM orders o 
            JOIN masters m ON o.master_id = m.id
            WHERE o.client_id = ? 
            AND o.status = 'active'
            AND o.created_at < ?
            ORDER BY o.created_at ASC
            LIMIT 1
        """, (client_id, threshold))
        
        row = cur.fetchone()
        return dict(row) if row else None

    async def complete_order(self, order_id: int, rating: int = None, review: str = None, price: int = None):
        """Complete an order"""
        if rating is not None:
             self.conn.execute(
                "UPDATE orders SET status='completed', completed_at=?, rating=?, review_text=?, price=? WHERE id=?",
                (datetime.datetime.utcnow().isoformat(), rating, review, price, order_id)
            )
        else:
            self.conn.execute(
                "UPDATE orders SET status='completed', completed_at=? WHERE id=?",
                (datetime.datetime.utcnow().isoformat(), order_id)
            )
        self.conn.commit()

    async def search_masters(self, category_ids: list[int], district_ids: list[int], exclude_user_id: int = None):
        """Search masters by category and district IDs
        
        Args:
            category_ids: List of category IDs to search
            district_ids: List of district IDs to search
            exclude_user_id: Optional user ID to exclude from results (e.g., when master searches as client)
        """
        if not category_ids or not district_ids:
            return []
            
        cat_placeholders = ','.join(['?'] * len(category_ids))
        dist_placeholders = ','.join(['?'] * len(district_ids))
        
        # Build exclusion clause if needed
        exclude_clause = ""
        args = category_ids + district_ids
        if exclude_user_id is not None:
            exclude_clause = "AND m.user_id != ?"
            args.append(exclude_user_id)
        
        sql = f"""
            SELECT DISTINCT m.*, u.username, u.telegram_id
            FROM masters m
            LEFT JOIN users u ON m.user_id = u.id
            JOIN master_categories mc ON m.id = mc.master_id
            JOIN master_districts md ON m.id = md.master_id
            LEFT JOIN (
            SELECT master_id, COUNT(*) AS completed_count
                FROM orders
                WHERE status = 'completed'
                GROUP BY master_id
            ) AS oc ON oc.master_id = m.id
            WHERE m.status NOT IN ('blocked')
            AND mc.category_id IN ({cat_placeholders})
            AND md.district_id IN ({dist_placeholders})
            {exclude_clause}
            ORDER BY 
                CASE WHEN m.status = 'active_premium' THEN 1 ELSE 2 END,
                m.rating DESC,
                COALESCE(oc.completed_count, 0) DESC;
        """
        cur = self.conn.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]

    async def update_master_rating(self, master_id: int):
        """ update master rating """
        self.conn.execute(
            "UPDATE masters SET rating = (SELECT AVG(rating) FROM orders WHERE master_id = ? AND status = 'completed') WHERE id = ?",
            (master_id, master_id)
        )
        self.conn.commit()

    async def get_master_order_stats(self, master_id: int):
        """Get order statistics for a master: total completed, count of rating > 4, total rated"""
        cur = self.conn.execute("""
            SELECT 
                COUNT(*) as total_orders,
                SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as satisfied_clients,
                COUNT(rating) as rated_orders
            FROM orders 
            WHERE master_id = ? AND status = 'completed'
        """, (master_id,))
        row = cur.fetchone()
        return dict(row) if row else {'total_orders': 0, 'satisfied_clients': 0, 'rated_orders': 0}

    async def create_concierge_request(self, user_id: int, categories: str, phone: str, name: str):
        """Create a new concierge request in service_requests table"""
        cur = self.conn.execute(
            "INSERT INTO service_requests (user_id, categories, phone, name) VALUES (?, ?, ?, ?)",
            (user_id, categories, phone, name)
        )
        self.conn.commit()
        return cur.lastrowid

    async def add_premium_request(self, master_id: int, user_id: int, status: str):
        """Add a premium application record"""
        cur = self.conn.execute(
            "INSERT INTO premium_requests (master_id, user_id, status) VALUES (?, ?, ?)",
            (master_id, user_id, status)
        )
        self.conn.commit()
        return cur.lastrowid


    async def get_order(self, order_id: int):
        """ get order by ID (for compatibility with existing code)"""
        cur = self.conn.execute("""
            SELECT o.*
            FROM orders o
            WHERE o.id = ?
        """, (order_id,))
        order = cur.fetchone()
        if not order:
            return None
        
        result = dict(order)
        return result

    async def get_client_orders(self, client_id: int):
        """Get all orders for a client"""
        cur = self.conn.execute("""
            SELECT o.*, m.name as master_name, m.phone as master_phone, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = ?
            ORDER BY CASE WHEN o.status = 'active' THEN 1 ELSE 2 END ASC, o.created_at DESC
        """, (client_id,))
        return [dict(r) for r in cur.fetchall()]

    async def get_active_orders_count(self, client_id: int) -> int:
        """Get count of active orders for a client"""
        cur = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE client_id = ? AND status = 'active'",
            (client_id,)
        )
        return cur.fetchone()['cnt']

    async def get_active_orders(self, client_id: int):
        """Get all active orders for a client with master details"""
        cur = self.conn.execute("""
            SELECT o.*, m.name as master_name, m.phone as master_phone, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = ? AND o.status = 'active'
            ORDER BY o.created_at DESC
        """, (client_id,))
        return [dict(r) for r in cur.fetchall()]

    async def get_completed_orders(self, client_id: int, limit: int = 10, offset: int = 0):
        """Get completed orders for a client with pagination"""
        cur = self.conn.execute("""
            SELECT o.*, m.name as master_name, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = ? AND o.status = 'completed'
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (client_id, limit, offset))
        return [dict(r) for r in cur.fetchall()]

    async def get_completed_orders_count(self, client_id: int) -> int:
        """Get count of completed orders for a client"""
        cur = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE client_id = ? AND status = 'completed'",
            (client_id,)
        )
        return cur.fetchone()['cnt']

    # ===== Client Profiles API =====
    async def get_client_profile(self, user_id: int):
        """Get client profile by user_id"""
        cur = self.conn.execute('SELECT * FROM client_profiles WHERE user_id=?', (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    async def create_client_profile(self, user_id: int, phone: str = None, phone_verified: bool = False):
        """Create a new client profile"""
        normalized_phone = normalize_phone(phone) if phone else None
        cur = self.conn.execute(
            """INSERT INTO client_profiles (user_id, phone, phone_verified, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, normalized_phone, 1 if phone_verified else 0, 
             datetime.datetime.utcnow().isoformat(), datetime.datetime.utcnow().isoformat())
        )
        self.conn.commit()
        return cur.lastrowid

    async def update_client_phone(self, user_id: int, phone: str, phone_verified: bool = True):
        """Update client phone number"""
        normalized_phone = normalize_phone(phone)
        cur = self.conn.execute(
            """UPDATE client_profiles SET phone=?, phone_verified=?, updated_at=? WHERE user_id=?""",
            (normalized_phone, 1 if phone_verified else 0, datetime.datetime.utcnow().isoformat(), user_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    async def get_or_create_client_profile(self, user_id: int):
        """Get existing client profile or create new one"""
        profile = await self.get_client_profile(user_id)
        if profile:
            return profile
        
        # Create new profile
        await self.create_client_profile(user_id)
        return await self.get_client_profile(user_id)

    async def update_client_rating(self, user_id: int):
        """Update client rating based on orders where master rated them"""
        # Calculate average from client_rating in orders
        cur = self.conn.execute("""
            SELECT AVG(client_rating) as avg_rating 
            FROM orders 
            WHERE client_id = ? AND client_rating IS NOT NULL
        """, (user_id,))
        row = cur.fetchone()
        avg_rating = row['avg_rating'] if row and row['avg_rating'] else 5.0
        
        self.conn.execute(
            """UPDATE client_profiles SET rating=?, updated_at=? WHERE user_id=?""",
            (avg_rating, datetime.datetime.utcnow().isoformat(), user_id)
        )
        self.conn.commit()

    async def get_client_order_stats(self, user_id: int):
        """Get client order statistics (completed and cancelled counts)"""
        cur = self.conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed,
                COALESCE(SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END), 0) as cancelled
            FROM orders WHERE client_id = ?
        """, (user_id,))
        row = cur.fetchone()
        return {
            'completed': row['completed'] if row else 0,
            'cancelled': row['cancelled'] if row else 0
        }

    async def update_client_order_stats(self, user_id: int):
        """Update client profile with order statistics"""
        stats = await self.get_client_order_stats(user_id)
        self.conn.execute(
            """UPDATE client_profiles SET total_completed=?, total_cancelled=?, updated_at=? WHERE user_id=?""",
            (stats['completed'], stats['cancelled'], datetime.datetime.utcnow().isoformat(), user_id)
        )
        self.conn.commit()

    async def rate_client(self, order_id: int, rating: int):
        """Master rates client after order completion"""
        self.conn.execute(
            """UPDATE orders SET client_rating=? WHERE id=?""",
            (rating, order_id)
        )
        self.conn.commit()
        
        # Get the client_id to update their rating
        cur = self.conn.execute("SELECT client_id FROM orders WHERE id=?", (order_id,))
        row = cur.fetchone()
        if row:
            await self.update_client_rating(row['client_id'])

    async def get_client_reviews_for_masters(self, user_id: int):
        """Get all reviews/ratings this client has given to masters"""
        cur = self.conn.execute("""
            SELECT o.*, m.name as master_name, c.key_field as category_key
            FROM orders o
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN categories c ON o.category_id = c.id
            WHERE o.client_id = ? AND o.rating IS NOT NULL
            ORDER BY o.completed_at DESC
        """, (user_id,))
        return [dict(r) for r in cur.fetchall()]

    # ===== Reputation System API =====
    async def get_criteria(self, role_client: bool):
        """Get reputation criteria for clients (True) or masters (False)"""
        cur = self.conn.execute(
            "SELECT * FROM reputation_criteria WHERE role_client=? ORDER BY group_key, id", 
            (1 if role_client else 0,)
        )
        return [dict(r) for r in cur.fetchall()]

    async def save_votes(self, from_client: bool, order_id: int, criterion_ids: list[int]):
        """Save reputation votes for an order, clearing previous ones for same direction"""
        cur = self.conn.cursor()
        # Delete old votes
        cur.execute(
            "DELETE FROM reputation_votes WHERE order_id=? AND from_client=?",
            (order_id, 1 if from_client else 0)
        )
        # Insert new votes
        for cid in criterion_ids:
            cur.execute(
                "INSERT INTO reputation_votes (from_client, order_id, criterion_id) VALUES (?, ?, ?)",
                (1 if from_client else 0, order_id, cid)
            )
        self.conn.commit()

    async def get_user_reputation_stats(self, user_id: int):
        """Get reputation statistics for a user both as master and as client"""
        # Get stats AS MASTER (votes from clients)
        master = await self.get_master_by_user_id(user_id)
        master_stats = {}
        master_total = 0
        
        # Get ALL master criteria first
        all_master_criteria = await self.get_criteria(role_client=True)
        for crit in all_master_criteria:
            master_stats[crit['code_key']] = 0.0

        if master:
            master_id = master['id']
            # Total orders that have at least one vote from client
            cur = self.conn.execute("""
                SELECT COUNT(DISTINCT order_id) as total 
                FROM reputation_votes rv
                JOIN orders o ON rv.order_id = o.id
                WHERE o.master_id = ? AND rv.from_client = 1
            """, (master_id,))
            master_total = cur.fetchone()['total']
            
            if master_total > 0:
                cur = self.conn.execute("""
                    SELECT rc.code_key, COUNT(rv.id) as count
                    FROM reputation_criteria rc
                    JOIN reputation_votes rv ON rc.id = rv.criterion_id
                    JOIN orders o ON rv.order_id = o.id
                    WHERE o.master_id = ? AND rv.from_client = 1
                    GROUP BY rc.id
                """, (master_id,))
                for row in cur.fetchall():
                    master_stats[row['code_key']] = {
                        'percent': round((row['count'] / master_total) * 100, 1),
                        'count': row['count']
                    }
        else:
            # Not a master, but we still want to ensure the structure is consistent if called
            pass

        for key, val in master_stats.items():
            if not isinstance(val, dict):
                master_stats[key] = {'percent': 0.0, 'count': 0}

        # Get stats AS CLIENT (votes from masters)
        cur = self.conn.execute("""
            SELECT COUNT(DISTINCT order_id) as total 
            FROM reputation_votes rv
            JOIN orders o ON rv.order_id = o.id
            WHERE o.client_id = ? AND rv.from_client = 0
        """, (user_id,))
        client_total = cur.fetchone()['total']
        
        client_stats = {}
        # Get ALL client criteria first
        all_client_criteria = await self.get_criteria(role_client=False)
        for crit in all_client_criteria:
            client_stats[crit['code_key']] = {'percent': 0.0, 'count': 0}

        if client_total > 0:
            cur = self.conn.execute("""
                SELECT rc.code_key, COUNT(rv.id) as count
                FROM reputation_criteria rc
                JOIN reputation_votes rv ON rc.id = rv.criterion_id
                JOIN orders o ON rv.order_id = o.id
                WHERE o.client_id = ? AND rv.from_client = 0
                GROUP BY rc.id
            """, (user_id,))
            for row in cur.fetchall():
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
