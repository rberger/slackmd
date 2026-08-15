"""Pure conversion core.

No macOS APIs, no filesystem, no network live in this module. Everything here is a
pure function of its input string, which is what makes it safe to run anywhere
(including the network-isolated Docker sandbox) and trivial to eval. See SAFETY.md.
"""

from __future__ import annotations

import json
import re

# A leading "Display Name  [4:38 PM]" line that Slack prepends when you copy a
# single message. Matched on the rendered text so it is independent of the exact
# HTML wrapper the Slack build uses.
_AUTHOR_HEADER_RE = re.compile(
    r"^\s*.+?\s*\[\d{1,2}:\d{2}\s*(?:AM|PM)\]\s*$", re.IGNORECASE
)

# Alnum-only placeholder so markdownify's underscore/asterisk escaping never touches
# an emoji shortcode (`:white_check_mark:` would otherwise become `:white\_...:`).
_EMOJI_TOKEN = "EMJI{}X"
_EMOJI_TOKEN_RE = re.compile(r"EMJI(\d+)X")

_BLOCK_KEYS = {"list", "blockquote", "header", "code-block"}


def _strip_author_header(md: str) -> str:
    """Drop a leading "Name [time]" line (and following blanks) if present."""
    lines = md.splitlines()
    if lines and _AUTHOR_HEADER_RE.match(lines[0]):
        i = 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        return "\n".join(lines[i:]).strip()
    return md


def _tidy(md: str) -> str:
    md = md.replace("\xa0", " ")
    md = "\n".join(line.rstrip() for line in md.splitlines())
    return re.sub(r"\n{3,}", "\n\n", md).strip()


def slack_html_to_markdown(html: str, *, include_author_header: bool = False) -> str:
    """Convert Slack's clipboard ``public.html`` into CommonMark.

    This is the source produced by *selecting text and pressing Cmd-C*. Lossy edges
    (see docs/SPEC.md section 5): @mentions arrive as display names, custom emoji as
    shortcodes only.
    """
    from bs4 import BeautifulSoup
    from markdownify import markdownify as _md

    soup = BeautifulSoup(html, "html.parser")

    shortcodes: list[str] = []
    for img in soup.find_all("img"):
        code = (img.get("data-stringify-emoji") or img.get("alt") or "").strip()
        if not code:
            aria = (img.get("aria-label") or "").strip()
            if aria:
                code = ":" + aria.removesuffix(" emoji").strip().replace(" ", "_") + ":"
        if code:
            img.replace_with(_EMOJI_TOKEN.format(len(shortcodes)))
            shortcodes.append(code)
        else:
            img.replace_with("")

    md = _md(str(soup), bullets="-", strong_em_symbol="*")
    md = _EMOJI_TOKEN_RE.sub(lambda m: shortcodes[int(m.group(1))], md)
    md = _tidy(md)

    if not include_author_header:
        md = _strip_author_header(md)
    return md


def clean_slack_markdown(text: str, *, include_author_header: bool = False) -> str:
    """Clean Slack's own ``text/markdown`` clipboard flavor into CommonMark.

    This is the source produced by the *Copy message* action. It is already
    near-CommonMark; Slack only over-escapes parentheses, which we unescape.
    """
    md = text.replace("\\(", "(").replace("\\)", ")")
    md = _tidy(md)
    if not include_author_header:
        md = _strip_author_header(md)
    return md


def quill_to_markdown(delta: str | dict, *, include_author_header: bool = False) -> str:
    """Render Slack's ``slack/texty`` Quill Delta into CommonMark.

    Highest-fidelity source: inline ``bold``/``italic``/``strike``/``code``/``link``
    attributes on text, block ``list``/``blockquote``/``header``/``code-block`` on the
    terminating newline (standard Quill semantics).
    """
    if isinstance(delta, str):
        delta = json.loads(delta)
    ops = delta.get("ops", [])

    lines: list[tuple[dict, str]] = []
    cur: list[str] = []

    def render_inline(text: str, attrs: dict) -> str:
        if not text:
            return ""
        md = text
        if attrs.get("link"):
            md = f"[{md}]({attrs['link']})"
        if attrs.get("code"):
            md = f"`{md}`"
        if attrs.get("bold") and attrs.get("italic"):
            md = f"***{md}***"
        elif attrs.get("bold"):
            md = f"**{md}**"
        elif attrs.get("italic"):
            md = f"*{md}*"
        if attrs.get("strike"):
            md = f"~~{md}~~"
        return md

    def flush(block: dict | None) -> None:
        lines.append((block or {}, "".join(cur).rstrip()))
        cur.clear()

    for op in ops:
        ins = op.get("insert")
        attrs = op.get("attributes") or {}
        if isinstance(ins, dict):  # embed (e.g. emoji): keep a shortcode if present
            emoji = ins.get("emoji") if isinstance(ins.get("emoji"), str) else None
            if emoji:
                cur.append(emoji if emoji.startswith(":") else f":{emoji}:")
            continue
        if not isinstance(ins, str):
            continue
        if ins == "\n" and (set(attrs) & _BLOCK_KEYS):
            flush(attrs)
            continue
        inline = {k: v for k, v in attrs.items() if k not in _BLOCK_KEYS}
        parts = ins.split("\n")
        for i, part in enumerate(parts):
            if part:
                cur.append(render_inline(part, inline))
            if i < len(parts) - 1:
                flush(None)
    if "".join(cur).strip():
        flush(None)

    out: list[str] = []
    for block, text in lines:
        if block.get("list") == "bullet":
            out.append(f"- {text}")
        elif block.get("list") == "ordered":
            out.append(f"1. {text}")
        elif block.get("blockquote"):
            out.append(f"> {text}")
        elif block.get("header"):
            out.append("#" * int(block["header"]) + f" {text}")
        else:
            out.append(text)

    md = _tidy("\n".join(out))
    if not include_author_header:
        md = _strip_author_header(md)
    return md


def mrkdwn_to_markdown(text: str) -> str:
    """Convert Slack ``mrkdwn`` into CommonMark. Hand-rolled tokenizer (Phase 2/4)."""
    raise NotImplementedError("Phase 2/4")


def markdown_to_mrkdwn(md: str) -> str:
    """Convert CommonMark into Slack ``mrkdwn`` text, a paste target (Phase 3)."""
    raise NotImplementedError("Phase 3")


def markdown_to_blockkit(md: str) -> list[dict]:
    """Convert CommonMark into Slack Block Kit ``rich_text`` JSON (Phase 4)."""
    raise NotImplementedError("Phase 4")
