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
                "value": "```ini\nBalance: Not available in public profile data\n```",
                "inline": True,
            },
            {
                "name": "💎 Limiteds",
                "value": "```ini\nNot queried by this safe version\n```",
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
                "value": "```diff\nPublic game history not verified here\n```",
                "inline": True,
            },
            {
                "name": "🛡️ Settings",
                "value": "```diff\nPrivate security settings omitted\n```",
                "inline": True,
            },
        ],
        "footer": {"text": f"VERSION_02 | {display_name[:150]}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "username": f"{display_name[:70]} | Stats",
        "avatar_url": avatar_url,
        "embeds": [embed],
    }


def send_webhook(webhook_url: str, payload: dict) -> bool:
    """Send the embed and report Discord's response without exposing the URL."""
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=TIMEOUT,
        )
    except requests.Timeout:
        print("ERROR: Discord webhook request timed out.", file=sys.stderr)
        return False
    except requests.RequestException as exc:
        print(
            f"ERROR: Discord request failed ({type(exc).__name__}).",
            file=sys.stderr,
        )
        return False

    print(f"DEBUG: Discord webhook HTTP status: {response.status_code}")

    if response.status_code in (200, 204):
        print("SUCCESS: Discord accepted the embed.")
        return True

    print("ERROR: Discord rejected the embed.")
    print("Response:", response.text[:500])
    return False


def main() -> int:
    webhook_url = os.environ.get(DISCORD_WEBHOOK_ENV, "").strip()
    if not webhook_url:
        print(
            f"ERROR: {DISCORD_WEBHOOK_ENV} is missing from this process environment.",
            file=sys.stderr,
        )
        return 1

    if len(sys.argv) != 2:
        print(
            "Usage: python core_extractor.py <public_roblox_user_id>",
            file=sys.stderr,
        )
        return 2

    try:
        user_id = int(sys.argv[1])
        if user_id <= 0:
            raise ValueError
    except ValueError:
        print("ERROR: Provide a positive numeric public Roblox user ID.", file=sys.stderr)
        return 2

    try:
        profile = fetch_public_profile(user_id)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        print(f"ERROR: Public Roblox profile request returned HTTP {status}.", file=sys.stderr)
        return 1
    except requests.RequestException as exc:
        print(f"ERROR: Roblox profile request failed ({type(exc).__name__}).", file=sys.stderr)
        return 1
    except ValueError:
        print("ERROR: Roblox returned invalid JSON for the public profile.", file=sys.stderr)
        return 1

    payload = build_embed(user_id, profile)
    return 0 if send_webhook(webhook_url, payload) else 1


if __name__ == "__main__":
    raise SystemExit(main())
