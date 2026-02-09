from utils.i18n import get_category_name, get_district_name

class CacheService:
    def __init__(self):
        # ID -> { 'key': str, 'names': {lang: str} }
        self.categories = {}
        self.districts = {}
        
        # Key -> ID
        self.cat_key_to_id = {}
        self.dist_key_to_id = {}

    async def load(self, db):
        """Load all categories and districts from DB into memory"""
        # Load Categories
        all_cats = await db.get_all_categories()
        self.categories = {}
        self.cat_key_to_id = {}
        
        for cat in all_cats:
            c_id = cat['id']
            key = cat['key_field']
            self.categories[c_id] = {
                'key': key,
                'names': {
                    'ru': get_category_name(key, 'ru'),
                    'tr': get_category_name(key, 'tr')
                }
            }
            if key:
                self.cat_key_to_id[key] = c_id

        # Load Districts
        all_dists = await db.get_districts()
        self.districts = {}
        self.dist_key_to_id = {}
        
        for dist in all_dists:
            d_id = dist['id']
            key = dist['key_field']
            self.districts[d_id] = {
                'key': key,
                'names': {
                    'ru': get_district_name(key, 'ru'),
                    'tr': get_district_name(key, 'tr')
                }
            }
            if key:
                self.dist_key_to_id[key] = d_id
                
        print(f"Cache loaded: {len(self.categories)} categories, {len(self.districts)} districts")

    def get_category_id(self, key: str) -> int:
        return self.cat_key_to_id.get(key)

    def get_district_id(self, key: str) -> int:
        return self.dist_key_to_id.get(key)
        
    def get_category_name(self, cat_id: int, lang: str = 'ru') -> str:
        cat = self.categories.get(cat_id)
        if not cat:
            return f"Unknown Category {cat_id}"
        return cat['names'].get(lang, cat['names'].get('ru'))

    def get_district_name(self, dist_id: int, lang: str = 'ru') -> str:
        dist = self.districts.get(dist_id)
        if not dist:
            return f"Unknown District {dist_id}"
        return dist['names'].get(lang, dist['names'].get('ru'))
