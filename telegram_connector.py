import json
import os
import urllib.request
import urllib.error
import threading
from dotenv import load_dotenv

load_dotenv()

telegram_token = os.getenv("TELEGRAM_TOKEN")
telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
telegram_state_file = "telegram_state.json"

if os.path.exists(telegram_state_file):
    try:
        with open(telegram_state_file) as f:
            last_received_update_id = json.load(f).get("last_received_update_id", 0)
    except Exception:
        last_received_update_id = 0
else:
    last_received_update_id = 0

def telegram_enabled() -> bool:
    return os.getenv("ENABLE_TELEGRAM", "false").lower() in ["true", "1", "yes"]

def send_telegram_message(message: str) -> None:
    if not telegram_token or not telegram_chat_id or not telegram_enabled():
        return
    if len(message) > 4000:
        message = message[:3980] + "\n\n(...truncated)"
        print("⚙️ Message truncated to fit Telegram limits.")
    
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = json.dumps({"chat_id": telegram_chat_id, "text": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram message: {e}")

def read_telegram_messages() -> list[str]:
    global last_received_update_id
    if not telegram_token or not telegram_enabled():
        return []
        
    url = f"https://api.telegram.org/bot{telegram_token}/getUpdates?offset={last_received_update_id + 1}&timeout=1"
    try:
        response = urllib.request.urlopen(url, timeout=35)
        data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
        
    updates = data.get("result", [])
    if updates and len(updates) > 0:
        last_received_update_id = updates[-1]["update_id"]
        with open(telegram_state_file, "w") as f:
            json.dump({"last_received_update_id": last_received_update_id}, f)
            
    return [
        update["message"]["text"]
        for update in updates
        if "message" in update and "text" in update["message"]
    ]
