# ================================
# utils/sheets.py — Google Sheets API
# ================================

import json
import logging
from typing import List, Dict, Optional
import gspread
from google.oauth2.service_account import Credentials

from config import SHEETS_CREDS_JSON, SHEETS_ID

logger = logging.getLogger(__name__)

class SheetsManager:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.initialized = False
    
    async def init(self):
        """Initialize Google Sheets connection"""
        if not SHEETS_ID or SHEETS_CREDS_JSON == "{}":
            logger.warning("⚠️  Google Sheets not configured (SHEETS_ID or SHEETS_CREDS missing)")
            return
        
        try:
            # Parse service account JSON
            creds_dict = json.loads(SHEETS_CREDS_JSON)
            creds = Credentials.from_service_account_info(creds_dict)
            
            # Auth
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(SHEETS_ID)
            self.initialized = True
            
            logger.info("✅ Google Sheets connected")
        except Exception as e:
            logger.error(f"❌ Sheets init error: {e}")
    
    async def add_unverified_master(self, master_data: Dict):
        """Write unverified master to 'unverified_masters' sheet"""
        if not self.initialized:
            logger.warning("Sheets not initialized, skipping")
            return
        
        try:
            ws = self.sheet.worksheet("unverified_masters")
            
            row = [
                master_data['id'],
                master_data['name'],
                master_data['phone'],
                ", ".join(master_data['districts']),
                ", ".join(master_data['categories']),
                master_data['description'],
                "pending",  # status
                master_data['created_at'].isoformat() if master_data['created_at'] else ""
            ]
            
            ws.append_row(row)
            logger.info(f"✅ Master {master_data['id']} added to Sheets")
        except Exception as e:
            logger.error(f"❌ Sheets append error: {e}")
    
    async def approve_master_in_sheets(self, master_id: int):
        """Mark master as approved in Sheets"""
        if not self.initialized:
            return
        
        try:
            ws = self.sheet.worksheet("unverified_masters")
            cell = ws.find(str(master_id))
            
            if cell:
                ws.update_cell(cell.row, 7, "approved")  # status column
                logger.info(f"✅ Master {master_id} approved in Sheets")
        except Exception as e:
            logger.error(f"❌ Sheets update error: {e}")
    
    async def get_pending_masters(self) -> List[Dict]:
        """Get all pending masters from Sheets"""
        if not self.initialized:
            return []
        
        try:
            ws = self.sheet.worksheet("unverified_masters")
            rows = ws.get_all_records()
            
            return [r for r in rows if r.get('status') == 'pending']
        except Exception as e:
            logger.error(f"❌ Sheets read error: {e}")
            return []

# Global instance
sheets_manager = SheetsManager()
