"""Clipboard source detection and routing.

Slack puts different rich flavors on the clipboard depending on how you copy:

- *Select text + Cmd-C*  -> ``public.html``
- *Copy message* action  -> ``text/markdown`` and ``slack/texty`` (Quill Delta),
  both packed inside Chromium's ``org.chromium.web-custom-data`` blob.

This module is pure: it parses the raw ``web-custom-data`` bytes and routes a dict of
available flavors to the highest-fidelity converter. The macOS pasteboard read lives
in the CLI adapter, not here, so this all runs in the sandbox.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .core import clean_slack_markdown, quill_to_markdown, slack_html_to_markdown

# Highest fidelity first.
SOURCE_PRIORITY = ("text/markdown", "slack/texty", "public.html", "text/plain")


@dataclass
class Conversion:
    markdown: str
    source: str


def parse_chromium_custom_data(blob: bytes) -> dict[str, str]:
    """Parse ``org.chromium.web-custom-data`` (a base::Pickle) into {mime: value}.

    Layout: ``[uint32 payload_size][uint32 count]`` then ``count`` pairs of
    String16 (``[uint32 n_utf16][utf16-le bytes]``), each field 4-byte aligned.
    """
    off = 4  # skip the payload-size header
    out: dict[str, str] = {}

    def read_u32() -> int:
        nonlocal off
        v = struct.unpack_from("<I", blob, off)[0]
        off += 4
        return v

    def read_str16() -> str:
        nonlocal off
        n = read_u32()  # number of UTF-16 code units
        raw = blob[off : off + n * 2]
        off += n * 2
        if off % 4:  # 4-byte alignment
            off += 4 - (off % 4)
        return raw.decode("utf-16-le", errors="replace")

    count = read_u32()
    for _ in range(count):
        key = read_str16()
        out[key] = read_str16()
    return out


def route(sources: dict[str, str], *, include_author_header: bool = False) -> Conversion:
    """Pick the highest-fidelity available source and convert it to CommonMark."""
    for key in SOURCE_PRIORITY:
        if key not in sources or not sources[key]:
            continue
        if key == "text/markdown":
            md = clean_slack_markdown(sources[key], include_author_header=include_author_header)
        elif key == "slack/texty":
            md = quill_to_markdown(sources[key], include_author_header=include_author_header)
        elif key == "public.html":
            md = slack_html_to_markdown(sources[key], include_author_header=include_author_header)
        else:  # text/plain: already rendered, no formatting to recover
            md = sources[key].strip()
        return Conversion(markdown=md, source=key)
    raise ValueError("no convertible Slack source on the clipboard")
