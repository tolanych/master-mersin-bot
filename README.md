# Mersin Masters Bot - Production-ready MVP Telegram

## QUICK START Local dev

```bash
# 1. Setup Python env
python -m venv venv && source venv/bin/activate

# 2. Install deps
pip install -r requirements.txt

# 3. Create .env
cp .env.example .env

# 4. Edit .env
# BOT_TOKEN=xxx (from BotFather)
# USE_POLLING=true
# ADMIN_IDS=your_telegram_id

# 5. Run
python main.py
```