"""Thin CLI + clipboard adapter.

This is the only layer that touches the macOS pasteboard. The Slack poster (`post`)
is dry-run by default and requires an explicit `--send` flag plus `SLACK_BOT_TOKEN`
in the environment (and an optional channel allowlist); see SAFETY.md.
"""

from __future__ import annotations

import argparse
import sys

from .core import markdown_to_blockkit, markdown_to_html, markdown_to_mrkdwn
from .sources import route


def _clipboard_sources() -> dict[str, str]:
    """Gather every rich Slack flavor currently on the macOS pasteboard."""
    from AppKit import NSPasteboard  # macOS extra; imported lazily so core stays pure

    from .sources import parse_chromium_custom_data

    pb = NSPasteboard.generalPasteboard()
    sources: dict[str, str] = {}

    html = pb.stringForType_("public.html")
    if html:
        sources["public.html"] = html

    data = pb.dataForType_("org.chromium.web-custom-data")
    if data:
        custom = parse_chromium_custom_data(bytes(data))
        for key in ("text/markdown", "slack/texty"):
            if custom.get(key):
                sources[key] = custom[key]

    plain = pb.stringForType_("public.utf8-plain-text")
    if plain:
        sources["text/plain"] = plain

    return sources


def _write_clipboard_text(text: str) -> None:
    from AppKit import NSPasteboard

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, "public.utf8-plain-text")


def _write_clipboard_rich(html: str, plain: str) -> None:
    """Write HTML (for Slack's composer to import) with a plain-text fallback."""
    from AppKit import NSPasteboard

    pb = NSPasteboard.generalPasteboard()
    pb.declareTypes_owner_(["public.html", "public.utf8-plain-text"], None)
    pb.setString_forType_(html, "public.html")
    pb.setString_forType_(plain, "public.utf8-plain-text")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slackmd", description="Slack <-> Markdown")
    sub = parser.add_subparsers(dest="cmd")

    fs = sub.add_parser(
        "from-slack", help="Convert a copied Slack message to Markdown (best source wins)"
    )
    fs.add_argument(
        "--keep-author", action="store_true", help="Keep the author/timestamp header line"
    )
    fs.add_argument(
        "--copy", action="store_true", help="Write the Markdown back to the clipboard"
    )

    ts = sub.add_parser(
        "to-slack", help="Convert Markdown (clipboard plain text) to Slack mrkdwn"
    )
    ts.add_argument(
        "--copy", action="store_true", help="Write the mrkdwn back to the clipboard"
    )
    ts.add_argument(
        "--no-escape",
        action="store_true",
        help="Do not entity-escape & < > (for pasting into the composer)",
    )

    sub.add_parser(
        "to-blockkit",
        help="Convert Markdown (clipboard) to Block Kit blocks JSON (for chat.postMessage)",
    )

    pp = sub.add_parser(
        "post",
        help="Post clipboard Markdown to a Slack channel as Block Kit (dry-run by default)",
    )
    pp.add_argument("--channel", required=True, help="Channel ID, e.g. C0123ABCD")
    pp.add_argument("--send", action="store_true", help="Actually send (default is dry-run)")
    pp.add_argument("--text", help="Plain-text fallback (default: mrkdwn of the Markdown)")

    args = parser.parse_args(argv)

    if args.cmd == "from-slack":
        sources = _clipboard_sources()
        if not sources:
            print(
                "No Slack content on the clipboard. Copy a Slack message first.",
                file=sys.stderr,
            )
            return 1
        conv = route(sources, include_author_header=args.keep_author)
        if args.copy:
            _write_clipboard_text(conv.markdown)
        print(conv.markdown)
        print(f"[source: {conv.source}]", file=sys.stderr)
        return 0

    if args.cmd == "to-slack":
        from AppKit import NSPasteboard

        pb = NSPasteboard.generalPasteboard()
        md = pb.stringForType_("public.utf8-plain-text")
        if not md:
            print("No Markdown text on the clipboard.", file=sys.stderr)
            return 1
        mrkdwn = markdown_to_mrkdwn(md, escape=not args.no_escape)
        if args.copy:
            # Slack's composer imports HTML on paste (plain mrkdwn renders literally),
            # so write HTML as the rich flavor with mrkdwn as the plain-text fallback.
            _write_clipboard_rich(markdown_to_html(md), mrkdwn)
        print(mrkdwn)
        return 0

    if args.cmd == "to-blockkit":
        import json

        from AppKit import NSPasteboard

        pb = NSPasteboard.generalPasteboard()
        md = pb.stringForType_("public.utf8-plain-text")
        if not md:
            print("No Markdown text on the clipboard.", file=sys.stderr)
            return 1
        print(json.dumps({"blocks": markdown_to_blockkit(md)}, indent=2))
        return 0

    if args.cmd == "post":
        import json
        import os

        from AppKit import NSPasteboard

        from .slack import build_message, post_message

        pb = NSPasteboard.generalPasteboard()
        md = pb.stringForType_("public.utf8-plain-text")
        if not md:
            print("No Markdown text on the clipboard.", file=sys.stderr)
            return 1
        payload = build_message(md, args.channel, text=args.text)

        if not args.send:
            print(json.dumps(payload, indent=2))
            print(
                "DRY RUN: nothing sent. Re-run with --send and SLACK_BOT_TOKEN set to post.",
                file=sys.stderr,
            )
            return 0

        token = os.environ.get("SLACK_BOT_TOKEN")
        if not token:
            print("SLACK_BOT_TOKEN is not set in the environment.", file=sys.stderr)
            return 1
        allow = os.environ.get("SLACK_ALLOWED_CHANNELS")
        if allow and args.channel not in {c.strip() for c in allow.split(",") if c.strip()}:
            print(
                f"channel {args.channel} is not in SLACK_ALLOWED_CHANNELS.", file=sys.stderr
            )
            return 1
        resp = post_message(token, payload)
        if resp.get("ok"):
            print(f"posted to {args.channel} (ts={resp.get('ts')})")
            return 0
        print(f"Slack API error: {resp.get('error')}", file=sys.stderr)
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
