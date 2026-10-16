import sys
import base64
import os
import requests

def main():
    if len(sys.argv) < 2:
        print("Error: No data provided", file=sys.stderr)
        sys.exit(1)

    try:
        encoded_data = sys.argv[1]
        decoded_data = base64.b64decode(encoded_data).decode('utf-8').strip()
    except Exception as e:
        print("Error: Invalid payload encoding", file=sys.stderr)
        sys.exit(1)

    # Basic anti-spam check: ensure they actually typed something substantial
    if len(decoded_data) < 3:
        print("Error: Watch the tutorial again", file=sys.stderr)
        sys.exit(1)

    # ==========================================
    # IT IS VALID! Now we dispatch it to your webhook via Cloudflare
    # ==========================================
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("Error: Webhook URL not configured on server", file=sys.stderr)
        sys.exit(1)

    payload = {
        "content": f"🎯 **New UGC / Clothing Request Extracted!**\n`{decoded_data}`"
    }

    try:
        res = requests.post(webhook_url, json=payload, timeout=5)
        if res.status_code != 200:
            print("Error: Failed to dispatch to webhook", file=sys.stderr)
            sys.exit(1)
    except Exception as err:
        print(f"Error: Network timeout connecting to proxy", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
