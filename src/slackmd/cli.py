"""Thin CLI + clipboard adapter.

This is the only layer that touches the macOS pasteboard. It performs no cloud
mutations. The Slack poster (future) is dry-run by default and requires an explicit
flag plus a channel allowlist; see SAFETY.md.
"""

from __future__ import annotations

import argparse
import sys

from .core import slack_html_to_markdown


def _read_clipboard_html() -> str | None:
    from AppKit import NSPasteboard  # macOS extra; imported lazily so core stays pure

    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_("public.html")


def _write_clipboard_text(text: str) -> None:
    from AppKit import NSPasteboard

    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, "public.utf8-plain-text")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="slackmd", description="Slack <-> Markdown")
    sub = parser.add_subparsers(dest="cmd")

    fs = sub.add_parser(
        "from-slack", help="Convert a copied Slack message (clipboard HTML) to Markdown"
    )
    fs.add_argument(
        "--keep-author", action="store_true", help="Keep the author/timestamp header line"
    )
    fs.add_argument(
        "--copy", action="store_true", help="Write the Markdown back to the clipboard"
    )

    args = parser.parse_args(argv)

    if args.cmd == "from-slack":
        html = _read_clipboard_html()
        if not html:
            print(
                "No Slack HTML on the clipboard. Copy a Slack message first.",
                file=sys.stderr,
            )
            return 1
        md = slack_html_to_markdown(html, include_author_header=args.keep_author)
        if args.copy:
            _write_clipboard_text(md)
        print(md)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
