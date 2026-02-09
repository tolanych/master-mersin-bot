import time
from collections import OrderedDict
from config import USER_CACHE_TTL, USER_CACHE_MAX_SIZE

class UserCache:
    def __init__(self):
        self.cache = OrderedDict()
        self.ttl = USER_CACHE_TTL
        self.max_size = USER_CACHE_MAX_SIZE

    def get(self, telegram_id: int):
        if telegram_id in self.cache:
            data, timestamp = self.cache[telegram_id]
            if time.time() - timestamp < self.ttl:
                # Move to end (MRU)
                self.cache.move_to_end(telegram_id)
                return data
            else:
                # Expired
                del self.cache[telegram_id]
        return None

    def set(self, telegram_id: int, data: dict):
        if telegram_id in self.cache:
            self.cache.move_to_end(telegram_id)
        self.cache[telegram_id] = (data, time.time())
        
        # Enforce max size
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False) # Remove FIFO (oldest inserted/accessed)

    def invalidate(self, telegram_id: int):
        if telegram_id in self.cache:
            del self.cache[telegram_id]
            
    def clear(self):
        self.cache.clear()
