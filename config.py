"""
Configuration for Pharma Pro Telegram Bot.
All admin, subscription, path, and AI settings are defined here.
"""

# =======================
# TELEGRAM SETTINGS
# =======================
TELEGRAM_BOT_TOKEN = "8414730729:AAHh_82uw3y0bCC4FkMBJLP5V7xPSSY_BPU"

# Bootstrap admin IDs — these users automatically become admins on first launch.
# Additional admins are stored in DB (via Add Admin button).
ADMIN_IDS = [
    8008744998,     # Replace with your Telegram ID
]


# =======================
# FOLDER & DATABASE PATHS
# =======================
DB_PATH = "data/pharma_bot.db"
BOOKS_FOLDER = "books"
PENDING_PDFS_FOLDER = "pending_pdfs"

# Auto-create required folders
import os
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(BOOKS_FOLDER, exist_ok=True)
os.makedirs(PENDING_PDFS_FOLDER, exist_ok=True)


# =======================
# SUBSCRIPTION SETTINGS
# =======================
FREE_MESSAGES = 150
PREMIUM_PRICE_INR = 100    # Lifetime plan price

# Manual payment message (no automated verification)
PAYMENT_INSTRUCTIONS = """
💳 *Payment Instructions (Manual Verification)*

Amount: ₹100  
UPI ID: *yourupi@bank*  
Name: Your Name

After payment:
➡️ Upload the *payment screenshot* here  
➡️ Admin will verify manually  
➡️ Lifetime Pro will be activated

Thank you 🙏
"""


# =======================
# AI / LLM CONFIG
# =======================
LLM_API_BASE = "https://api.deepseek.com/v1/chat/completions"
LLM_API_KEY = "sk-89395d8aaacb47b99456f771daa5212c"
LLM_MODEL_NAME = "deepseek-chat"
LLM_TEMPERATURE = 0.2


# =======================
# BOT INFO
# =======================
BOT_NAME = "Pharma Pro Assistant"
