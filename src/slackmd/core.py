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


def _mrkdwn_escape(s: str) -> str:
    # Slack mrkdwn control chars, escaped as HTML entities (required for the API).
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markdown_to_html(md: str) -> str:
    """Render CommonMark to HTML, the rich flavor Slack's composer imports on paste.

    Pasting plain ``mrkdwn`` into Slack's WYSIWYG composer renders literally; pasting
    HTML makes the composer adopt the formatting (bold, links, lists, code, quotes).

    Slack collapses a ``<br>`` inside a ``<blockquote>`` on paste, so multi-line quotes
    are re-emitted as one ``<p>`` per line (which Slack keeps as separate quoted lines),
    preserving inline markup within each line.
    """
    from bs4 import BeautifulSoup
    from markdown_it import MarkdownIt

    raw = MarkdownIt("gfm-like", {"breaks": True}).disable("linkify").render(md)
    soup = BeautifulSoup(raw, "html.parser")

    for bq in soup.find_all("blockquote"):
        paras = bq.find_all("p", recursive=False) or [bq]
        lines_html: list[str] = []
        for p in paras:
            cur = ""
            for child in p.children:
                if getattr(child, "name", None) == "br":
                    if cur.strip():
                        lines_html.append(cur.strip())
                    cur = ""
                else:
                    cur += str(child)
            if cur.strip():
                lines_html.append(cur.strip())
        if len(lines_html) <= 1:
            continue  # single-line quote: leave as-is
        inner = "".join(f"<p>{ln}</p>" for ln in lines_html)
        new_bq = BeautifulSoup(f"<blockquote>{inner}</blockquote>", "html.parser")
        bq.replace_with(*new_bq.children)

    return str(soup)


def markdown_to_mrkdwn(md: str, *, escape: bool = True) -> str:
    """Convert CommonMark into Slack ``mrkdwn`` text (Phase 3, reverse direction).

    Documented degradations (docs/SPEC.md 4.3): headings -> ``*bold*`` line, links ->
    ``<url|label>``, ``**``->``*`` and ``*``->``_``, bullets -> ``•``, single-level
    blockquote, tables -> monospace block. Set ``escape=False`` to skip entity-escaping
    ``& < >`` (useful when the result is meant to be pasted, not sent via the API).
    """
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    esc = _mrkdwn_escape if escape else (lambda s: s)

    def inline(node) -> str:
        t = node.type
        if t == "text":
            return esc(node.content)
        if t == "code_inline":
            return f"`{node.content}`"
        if t in ("softbreak", "hardbreak"):
            return "\n"
        if t == "strong":
            return "*" + "".join(inline(c) for c in node.children) + "*"
        if t == "em":
            return "_" + "".join(inline(c) for c in node.children) + "_"
        if t == "s":
            return "~" + "".join(inline(c) for c in node.children) + "~"
        if t == "link":
            href = node.attrs.get("href", "")
            label = "".join(inline(c) for c in node.children)
            return f"<{href}|{label}>" if label and label != href else f"<{href}>"
        if t == "image":
            alt = node.attrs.get("alt") or "".join(inline(c) for c in node.children)
            return esc(alt)
        return "".join(inline(c) for c in node.children)

    def inline_of(node) -> str:
        # a block node whose first child is the "inline" container
        for c in node.children:
            if c.type == "inline":
                return inline(c)
        return "".join(inline(c) for c in node.children)

    def list_item(node, depth: int, marker: str) -> str:
        indent = "    " * depth
        head_parts: list[str] = []
        nested: list[str] = []
        for c in node.children:
            if c.type in ("bullet_list", "ordered_list"):
                nested.append(block(c, depth + 1))
            else:
                head_parts.append(block(c, depth))
        head = " ".join(p for p in head_parts if p).strip()
        line = f"{indent}{marker}{head}"
        if nested:
            line += "\n" + "\n".join(nested)
        return line

    def block(node, depth: int = 0) -> str:
        t = node.type
        if t == "root":
            return "\n\n".join(b for b in (block(c) for c in node.children) if b)
        if t == "paragraph":
            return inline_of(node)
        if t == "heading":
            return "*" + inline_of(node).strip() + "*"
        if t == "hr":
            return "──────────"
        if t == "blockquote":
            inner = "\n\n".join(b for b in (block(c, depth) for c in node.children) if b)
            return "\n".join((f"> {ln}" if ln else ">") for ln in inner.split("\n"))
        if t in ("fence", "code_block"):
            return "```\n" + node.content.rstrip("\n") + "\n```"
        if t == "bullet_list":
            return "\n".join(list_item(c, depth, "• ") for c in node.children)
        if t == "ordered_list":
            start = int(node.attrs.get("start", 1) or 1)
            return "\n".join(
                list_item(c, depth, f"{start + i}. ") for i, c in enumerate(node.children)
            )
        if t == "table":
            return _mrkdwn_table(node, esc)
        if t == "inline":
            return inline(node)
        return "\n\n".join(b for b in (block(c, depth) for c in node.children) if b)

    tree = SyntaxTreeNode(MarkdownIt("gfm-like").disable("linkify").parse(md))
    return _tidy(block(tree))


def _bk_table_text(node) -> str:
    # Slack has no table type; render an aligned monospace block (shared by the
    # mrkdwn code-fence path and the Block Kit rich_text_preformatted path).
    rows: list[list[str]] = []
    for section in node.children:  # thead / tbody
        for tr in section.children:
            cells = []
            for cell in tr.children:  # th / td
                parts = []
                for c in cell.children:
                    if c.type == "inline":
                        parts.append("".join(_plain(x) for x in c.children))
                cells.append("".join(parts).strip())
            rows.append(cells)
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    widths = [0] * ncol
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))
    out = []
    for r in rows:
        padded = [(r[i] if i < len(r) else "").ljust(widths[i]) for i in range(ncol)]
        out.append("  ".join(padded).rstrip())
    return "\n".join(out)


def _mrkdwn_table(node, esc) -> str:
    body = _bk_table_text(node)
    return "```\n" + body + "\n```" if body else ""


def _plain(node) -> str:
    if node.type == "text" or node.type == "code_inline":
        return node.content
    if node.type in ("softbreak", "hardbreak"):
        return " "
    return "".join(_plain(c) for c in node.children)


def markdown_to_blockkit(md: str) -> list[dict]:
    """Convert CommonMark into Slack Block Kit blocks (Phase 4, highest fidelity).

    Returns a list of top-level blocks for ``chat.postMessage(blocks=...)``: a
    ``rich_text`` block carries sections, ``rich_text_list`` (with ``indent`` for
    nesting), ``rich_text_quote`` and ``rich_text_preformatted``; headings become
    ``header`` blocks and ``---`` becomes a ``divider``. Inline emphasis is flattened
    onto per-leaf ``style`` flags, links become ``link`` leaves, and ``:name:`` becomes
    an ``emoji`` leaf. No Slack user/channel IDs are available from Markdown, so those
    entities are out of scope here (see the SlackEnricher in docs/SPEC.md 4.5).
    """
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode

    def style_flags(style: dict) -> dict:
        return {k: True for k in ("bold", "italic", "strike", "code") if style.get(k)}

    def plain_text_of(node) -> str:
        if node.type in ("text", "code_inline"):
            return node.content
        if node.type in ("softbreak", "hardbreak"):
            return "\n"
        return "".join(plain_text_of(c) for c in node.children)

    def emoji_split(text: str, style: dict, out: list) -> None:
        s = style_flags(style)
        pos = 0
        for m in re.finditer(r":([a-z0-9_+'-]+):", text):
            if m.start() > pos:
                leaf = {"type": "text", "text": text[pos:m.start()]}
                if s:
                    leaf["style"] = s
                out.append(leaf)
            out.append({"type": "emoji", "name": m.group(1)})
            pos = m.end()
        if pos < len(text):
            leaf = {"type": "text", "text": text[pos:]}
            if s:
                leaf["style"] = s
            out.append(leaf)

    def render_inline(children, style: dict, out: list) -> None:
        for c in children:
            t = c.type
            if t == "text":
                emoji_split(c.content, style, out)
            elif t == "code_inline":
                out.append({"type": "text", "text": c.content, "style": style_flags({**style, "code": True})})
            elif t in ("softbreak", "hardbreak"):
                out.append({"type": "text", "text": "\n"})
            elif t == "strong":
                render_inline(c.children, {**style, "bold": True}, out)
            elif t == "em":
                render_inline(c.children, {**style, "italic": True}, out)
            elif t == "s":
                render_inline(c.children, {**style, "strike": True}, out)
            elif t == "link":
                leaf = {"type": "link", "url": c.attrs.get("href", ""), "text": plain_text_of(c)}
                s = style_flags(style)
                if s:
                    leaf["style"] = s
                out.append(leaf)
            elif t == "image":
                emoji_split(c.attrs.get("alt") or plain_text_of(c), style, out)
            else:
                render_inline(c.children, style, out)

    def leaves_of(block) -> list:
        inline = next((c for c in block.children if c.type == "inline"), None)
        out: list = []
        if inline is not None:
            render_inline(inline.children, {}, out)
        return out or [{"type": "text", "text": ""}]

    def emit_list(node, ordered: bool, indent: int, out: list) -> None:
        style = "ordered" if ordered else "bullet"
        items: list = []

        def flush():
            if items:
                out.append({"type": "rich_text_list", "style": style, "indent": indent, "elements": list(items)})
                items.clear()

        for li in node.children:
            para = next((c for c in li.children if c.type == "paragraph"), None)
            items.append({"type": "rich_text_section", "elements": leaves_of(para) if para else [{"type": "text", "text": ""}]})
            for c in li.children:
                if c.type in ("bullet_list", "ordered_list"):
                    flush()
                    emit_list(c, c.type == "ordered_list", indent + 1, out)
        flush()

    tree = SyntaxTreeNode(MarkdownIt("gfm-like").disable("linkify").parse(md))
    blocks: list = []
    rt: list = []

    def flush_rt():
        if rt:
            blocks.append({"type": "rich_text", "elements": list(rt)})
            rt.clear()

    for node in tree.children:
        t = node.type
        if t == "heading":
            flush_rt()
            blocks.append({"type": "header", "text": {"type": "plain_text", "text": plain_text_of(node)[:150], "emoji": True}})
        elif t == "hr":
            flush_rt()
            blocks.append({"type": "divider"})
        elif t == "paragraph":
            rt.append({"type": "rich_text_section", "elements": leaves_of(node)})
        elif t in ("bullet_list", "ordered_list"):
            if rt and rt[-1].get("type") == "rich_text_list":
                # Slack merges adjacent rich_text_list blocks into one run (taking the
                # first list's markers). An empty section between them keeps a following
                # ordered list numbered instead of inheriting the bullet style.
                rt.append({"type": "rich_text_section", "elements": [{"type": "text", "text": "\n"}]})
            emit_list(node, t == "ordered_list", 0, rt)
        elif t == "blockquote":
            for c in node.children:
                if c.type == "paragraph":
                    rt.append({"type": "rich_text_quote", "elements": leaves_of(c)})
                elif c.type in ("bullet_list", "ordered_list"):
                    emit_list(c, c.type == "ordered_list", 0, rt)
        elif t in ("fence", "code_block"):
            rt.append({"type": "rich_text_preformatted", "elements": [{"type": "text", "text": node.content.rstrip("\n")}]})
        elif t == "table":
            rt.append({"type": "rich_text_preformatted", "elements": [{"type": "text", "text": _bk_table_text(node)}]})

    flush_rt()
    return blocks
