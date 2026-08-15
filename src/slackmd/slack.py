"""Slack API adapter (network I/O; kept out of the pure core).

Posting is opt-in and guarded by the CLI: dry-run by default, an explicit ``--send``
flag, a bot token from the environment only, and an optional channel allowlist. See
SAFETY.md. Uses stdlib ``urllib`` so no extra dependency is required to post.
"""

from __future__ import annotations

from .core import markdown_to_blockkit, markdown_to_mrkdwn


def build_message(md: str, channel: str, *, text: str | None = None) -> dict:
    """Build a chat.postMessage payload from Markdown. Pure: no network."""
    return {
        "channel": channel,
        "blocks": markdown_to_blockkit(md),
        # A plain-text fallback for notifications and accessibility.
        "text": text if text is not None else markdown_to_mrkdwn(md),
    }


def post_message(token: str, payload: dict, *, timeout: int = 15) -> dict:
    """POST a payload to Slack's chat.postMessage. Returns the parsed JSON response."""
    import json
    import urllib.request

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed host)
        return json.load(resp)
