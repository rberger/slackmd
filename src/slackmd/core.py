"""Pure conversion core.

No macOS APIs, no filesystem, no network live in this module. Everything here is a
pure function of its input string, which is what makes it safe to run anywhere
(including the network-isolated Docker sandbox) and trivial to eval. See SAFETY.md.
"""

from __future__ import annotations

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


def slack_html_to_markdown(html: str, *, include_author_header: bool = False) -> str:
    """Convert Slack's clipboard ``public.html`` into CommonMark. PRIMARY path.

    Args:
        html: the ``public.html`` pasteboard flavor from a copied Slack message.
        include_author_header: keep the leading "Name [time]" line Slack prepends.
            Defaults to False, since the goal is clean body text for agent input.

    Lossy edges (see docs/SPEC.md section 5): @mentions arrive as display names,
    custom emoji as shortcodes only.
    """
    from bs4 import BeautifulSoup
    from markdownify import markdownify as _md

    soup = BeautifulSoup(html, "html.parser")

    # Replace emoji/images with a placeholder now, restore the shortcode after
    # markdownify so escaping cannot mangle it.
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

    # Normalize whitespace: nbsp -> space, drop trailing hard-break spaces, collapse
    # runs of blank lines.
    md = md.replace("\xa0", " ")
    md = "\n".join(line.rstrip() for line in md.splitlines())
    md = re.sub(r"\n{3,}", "\n\n", md).strip()

    if not include_author_header:
        lines = md.splitlines()
        if lines and _AUTHOR_HEADER_RE.match(lines[0]):
            i = 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            md = "\n".join(lines[i:]).strip()

    return md


def mrkdwn_to_markdown(text: str) -> str:
    """Convert Slack ``mrkdwn`` (from the API or a paste-back) into CommonMark.

    Hand-rolled tokenizer over Slack's documented ``<...>`` grammar (Phase 2/4).
    """
    raise NotImplementedError("Phase 2/4")


def markdown_to_mrkdwn(md: str) -> str:
    """Convert CommonMark into Slack ``mrkdwn`` text, a paste target (Phase 3, bonus).

    Applies documented degradations: headings -> bold line, tables -> monospace
    block, nested lists flattened. See docs/SPEC.md section 4.3.
    """
    raise NotImplementedError("Phase 3")


def markdown_to_blockkit(md: str) -> list[dict]:
    """Convert CommonMark into Slack Block Kit ``rich_text`` JSON (Phase 4, bonus).

    High-fidelity target: preserves real ordered/nested lists and canonical entities.
    """
    raise NotImplementedError("Phase 4")
