import sys
import base64
import os
import requests

def main():
    if len(sys.argv) < 2:
        return
    
    # Decode input script passed from Node.js
    decoded_script = base64.b64decode(sys.argv[1]).decode('utf-8')
    webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print("Webhook URL not configured on server.")
        return

    # Simple extraction logic
    payload = {
        "content": "✨ **NexusStudio Backend Alert**\nScript parsed successfully on Railway server."
    }

    requests.post(webhook_url, json=payload)

if __name__ == "__main__":
    main()
