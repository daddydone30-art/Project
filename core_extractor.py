       """Safe Discord embed sender using a public Roblox profile.

Usage:
    Set DISCORD_WEBHOOK_URL in the runtime environment.
    python core_extractor.py <public_roblox_user_id>

This version does not accept or process session cookies or send private account
security details.
"""

import os
import sys
from datetime import datetime, timezone

import requests

TIMEOUT = (5, 15)


def get_public_profile(user_id: int) -> dict:
    response = requests.get(
        f"https://users.roblox.com/v1/users/{user_id}",
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("Unexpected profile response")
    return data


def make_payload(user_id: int, profile: dict) -> dict:
    username = str(profile.get("name") or "Unknown User")
    display_name = str(profile.get("displayName") or username)
    created = profile.get("created") or ""
    age_days = 0

    if created:
        try:
            created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age_days = max(0, (datetime.now(timezone.utc) - created_at).days)
        except ValueError:
            print("WARNING: Invalid profile creation date.", file=sys.stderr)

    avatar_url = (
        "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size=420x420&format=Png&isCircular=false"
    )

    fields = [
        {
            "name": "🐱 Username",
            "value": f"```ini\n{username[:180]}\n```",
            "inline": False,
        },
        {
            "name": "📊 Account Stats",
            "value": f"```diff\n+ Account Age: {age_days} Days\n```",
            "inline": False,
        },
        {
            "name": "🪙 Robux",
            "value": "```ini\nBalance: Not available from public profile data\n```",
            "inline": True,
        },
        {
            "name": "💎 Limiteds",
            "value": "```ini\nNot queried by this public-profile version\n```",
            "inline": True,
        },
        {
            "name": "🚀 Summary",
            "value": "```ini\nNot available\n```",
            "inline": True,
        },
        {
            "name": "🔥 Payments",
            "value": "```diff\nPrivate account data omitted\n```",
            "inline": True,
        },
        {
            "name": "⭐ Games",
            "value": "```diff\nNot checked by this version\n```",
            "inline": True,
        },
        {
            "name": "🛡️ Settings",
            "value": "```diff\nPrivate security settings omitted\n```",
            "inline": True,
        },
    ]

    embed = {
        "title": "📢 Discord Notification 📢",
        "description": (
            "```ini\n[ ⚡ Stats ] • [ 🌐 Profile ]\n```\n"
            f"🔗 **[Roblox Profile](https://www.roblox.com/users/{user_id}/profile)**"
        ),
        "color": 0x2B2D31,
        "thumbnail": {"url": avatar_url},
        "fields": fields,
        "footer": {"text": f"VERSION_02 | {display_name[:150]}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "username": f"{display_name[:70]} | Stats",
        "avatar_url": avatar_url,
        "embeds": [embed],
    }


def send_embed(webhook_url: str, payload: dict) -> bool:
    try:
        response = requests.post(webhook_url, json=payload, timeout=TIMEOUT)
    except requests.Timeout:
        print("ERROR: Discord request timed out.", file=sys.stderr)
        return False
    except requests.RequestException as exc:
        print(f"ERROR: Discord network request failed ({type(exc).__name__}).", file=sys.stderr)
        return False

    print(f"Discord HTTP status: {response.status_code}")

    if response.status_code in (200, 204):
        print("SUCCESS: Discord accepted the embed.")
        return True

    print("ERROR: Discord rejected the embed.")
    print("Response:", response.text[:500])
    return False


def main() -> int:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("ERROR: DISCORD_WEBHOOK_URL is missing in this process.", file=sys.stderr)
        return 1

    if not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("ERROR: Check the webhook URL privately in your environment settings.", file=sys.stderr)
        return 1

    if len(sys.argv) != 2:
        print("Usage: python core_extractor.py <public_roblox_user_id>", file=sys.stderr)
        return 2

    try:
        user_id = int(sys.argv[1])
        if user_id <= 0:
            raise ValueError
    except ValueError:
        print("ERROR: User ID must be a positive integer.", file=sys.stderr)
        return 2

    try:
        profile = get_public_profile(user_id)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        print(f"ERROR: Roblox public profile returned HTTP {status}.", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"ERROR: Roblox profile request failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    except ValueError:
        print("ERROR: Roblox returned invalid profile data.", file=sys.stderr)
        return 1

    return 0 if send_embed(webhook_url, make_payload(user_id, profile)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
