# telegram_util.py

import requests
from config import TELEGRAM_BOT_TOKEN, GROUP_CHAT_ID


def send_telegram(msg: str):
    """Simple text message sender to main group."""
    if not TELEGRAM_BOT_TOKEN or not GROUP_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": GROUP_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        requests.post(url, data=data, timeout=15)
    except Exception as e:
        print(f"⚠ Telegram send error: {e}")


def send_document(file_path: str, caption: str = ""):
    """Send a document (TXT) with optional caption."""
    if not TELEGRAM_BOT_TOKEN or not GROUP_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": GROUP_CHAT_ID}
            if caption:
                data["caption"] = caption
                data["parse_mode"] = "HTML"
            requests.post(url, data=data, files=files, timeout=30)
    except Exception as e:
        print(f"⚠ Telegram document error: {e}")
