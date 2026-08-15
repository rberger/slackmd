"""Router + new-source converter tests. Synthetic, safe to commit and run anywhere."""

import struct

from slackmd import (
    Conversion,
    clean_slack_markdown,
    parse_chromium_custom_data,
    quill_to_markdown,
    route,
)


def test_clean_slack_markdown_unescapes_parens():
    out = clean_slack_markdown("deterministic tests \\(pytest, not an LLM\\) rock")
    assert out == "deterministic tests (pytest, not an LLM) rock"


def test_quill_inline_and_blocks():
    delta = {
        "ops": [
            {"insert": "Title", "attributes": {"bold": True, "link": "https://x.io"}},
            {"insert": "\nintro\n"},
            {"insert": "one"},
            {"insert": "\n", "attributes": {"list": "bullet"}},
            {"insert": "two"},
            {"insert": "\n", "attributes": {"list": "bullet"}},
            {"insert": "quoted"},
            {"insert": "\n", "attributes": {"blockquote": True}},
        ]
    }
    out = quill_to_markdown(delta)
    assert "**[Title](https://x.io)**" in out
    assert "- one" in out and "- two" in out
    assert "> quoted" in out


def test_quill_bold_italic():
    delta = {"ops": [{"insert": "hi", "attributes": {"bold": True, "italic": True}}, {"insert": "\n"}]}
    assert quill_to_markdown(delta) == "***hi***"


def test_router_prefers_markdown_over_quill_over_html():
    sources = {
        "text/markdown": "from-md",
        "slack/texty": '{"ops":[{"insert":"from-quill\\n"}]}',
        "public.html": "<b>from-html</b>",
        "text/plain": "from-plain",
    }
    conv = route(sources)
    assert isinstance(conv, Conversion)
    assert conv.source == "text/markdown"
    assert conv.markdown == "from-md"

    del sources["text/markdown"]
    assert route(sources).source == "slack/texty"
    del sources["slack/texty"]
    assert route(sources).source == "public.html"
    del sources["public.html"]
    assert route(sources).source == "text/plain"


def _encode_custom_data(entries: dict[str, str]) -> bytes:
    """Build a Chromium web-custom-data blob for round-trip testing the parser."""

    def str16(s: str) -> bytes:
        raw = s.encode("utf-16-le")
        buf = struct.pack("<I", len(s)) + raw
        if len(buf) % 4:
            buf += b"\x00" * (4 - (len(buf) % 4))
        return buf

    payload = struct.pack("<I", len(entries))
    for k, v in entries.items():
        payload += str16(k) + str16(v)
    return struct.pack("<I", len(payload)) + payload


def test_parse_chromium_custom_data_roundtrip():
    entries = {"text/markdown": "**hi** there", "slack/texty": '{"ops":[]}'}
    assert parse_chromium_custom_data(_encode_custom_data(entries)) == entries
