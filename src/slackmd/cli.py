"""Thin CLI + clipboard adapter.

This is the only layer that touches the macOS pasteboard. It performs no cloud
mutations. The Slack poster (future) is dry-run by default and requires an explicit
flag plus a channel allowlist; see SAFETY.md.
"""

from __future__ import annotations

import argparse
import sys

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

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
