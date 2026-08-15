"""Thin CLI + clipboard adapter.

This is the only layer that touches the macOS pasteboard. It performs no cloud
mutations. The Slack poster (future) is dry-run by default and requires an explicit
flag plus a channel allowlist; see SAFETY.md.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    print("slackmd: scaffolding only. Core conversion lands in Phase 1 (see docs/SPEC.md).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
