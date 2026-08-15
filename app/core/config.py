import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE", "")
    TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL", "")
    
    # DeepSeek
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    
    # WhatsApp
    WHATSAPP_ENABLED = os.getenv("WHATSAPP_ENABLED", "false").lower() == "true"
    WHATSAPP_RECIPIENT_1 = os.getenv("WHATSAPP_RECIPIENT_1", "")
    WHATSAPP_RECIPIENT_2 = os.getenv("WHATSAPP_RECIPIENT_2", "")
    
    # Control
    CONTROL_PASSWORD = os.getenv("CONTROL_PASSWORD", "admin123")
    
    # Alertes Prix
    ALERT_BTC_THRESHOLD = float(os.getenv("ALERT_BTC_THRESHOLD", "2.0"))
    ALERT_ETH_THRESHOLD = float(os.getenv("ALERT_ETH_THRESHOLD", "3.0"))
    ALERT_GOLD_THRESHOLD = float(os.getenv("ALERT_GOLD_THRESHOLD", "1.5"))
    
    # Binance
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    
    # Database
    DB_FILE = "data/analyses.json"
    
    # Telegram Notifications
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    TELEGRAM_NOTIFY_ENABLED = os.getenv("TELEGRAM_NOTIFY_ENABLED", "true").lower() == "true"
    
    # Gmail
    GMAIL_ENABLED = os.getenv("GMAIL_ENABLED", "false").lower() == "true"
    GMAIL_EMAIL = os.getenv("GMAIL_EMAIL", "")
    GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")
    GMAIL_RECIPIENT_1 = os.getenv("GMAIL_RECIPIENT_1", "")
    GMAIL_RECIPIENT_2 = os.getenv("GMAIL_RECIPIENT_2", "")
    
    # SendGrid
    SENDGRID_ENABLED = os.getenv("SENDGRID_ENABLED", "false").lower() == "true"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "")
    SENDGRID_TO_EMAIL = os.getenv("SENDGRID_TO_EMAIL", "")
    SENDGRID_TO_EMAIL_2 = os.getenv("SENDGRID_TO_EMAIL_2", "")

config = Config()