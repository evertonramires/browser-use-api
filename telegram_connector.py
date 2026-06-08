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

def send_telegram_photo(caption: str, photo_bytes: bytes) -> None:
    if not telegram_token or not telegram_chat_id or not telegram_enabled():
        return
        
    url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
    body.extend(f"{telegram_chat_id}\r\n".encode("utf-8"))
    
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
    body.extend(f"{caption}\r\n".encode("utf-8"))
    
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(b'Content-Disposition: form-data; name="photo"; filename="screenshot.png"\r\n')
    body.extend(b'Content-Type: image/png\r\n\r\n')
    body.extend(photo_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    
    req = urllib.request.Request(url, data=bytes(body))
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram photo: {e}")

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

is_waiting_for_reply = False
agent_reply_event = threading.Event()
latest_agent_reply = None

def wait_for_reply(question: str, timeout: int = 300, photo_bytes: bytes = None) -> str:
    global is_waiting_for_reply, latest_agent_reply
    
    if photo_bytes:
        send_telegram_photo(f"🙋 Agent needs your help:\n\n{question}", photo_bytes)
    else:
        send_telegram_message(f"🙋 Agent needs your help:\n\n{question}")
    
    # Wait for up to timeout seconds
    is_waiting_for_reply = True
    agent_reply_event.clear()
    latest_agent_reply = None
    
    # Drain any existing messages first so we don't read old ones
    _ = read_telegram_messages()
    
    agent_reply_event.wait(timeout)
    is_waiting_for_reply = False
    
    if latest_agent_reply:
        send_telegram_message(f"✅ Received your reply: {latest_agent_reply}")
        return latest_agent_reply
    else:
        return "Error: Human did not reply within the timeout period."
