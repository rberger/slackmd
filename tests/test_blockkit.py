"""markdown_to_blockkit (Block Kit rich_text) tests. Synthetic, safe to commit."""

from slackmd import markdown_to_blockkit


def _first(blocks, type_):
    return next(b for b in blocks if b["type"] == type_)


def _leaves(section):
    return section["elements"]


def test_paragraph_inline_styles():
    blocks = markdown_to_blockkit("plain **bold** _it_ ~~s~~ `c`")
    rt = _first(blocks, "rich_text")
    section = rt["elements"][0]
    assert section["type"] == "rich_text_section"
    leaves = _leaves(section)
    # find the styled leaves
    styles = {l["text"]: l.get("style", {}) for l in leaves if l["type"] == "text"}
    assert styles.get("bold") == {"bold": True}
    assert styles.get("it") == {"italic": True}
    assert styles.get("s") == {"strike": True}
    assert styles.get("c") == {"code": True}


def test_link_leaf():
    blocks = markdown_to_blockkit("[Kiro](https://kiro.dev)")
    leaves = _first(blocks, "rich_text")["elements"][0]["elements"]
    link = next(l for l in leaves if l["type"] == "link")
    assert link["url"] == "https://kiro.dev"
    assert link["text"] == "Kiro"


def test_bullet_and_nested_list_indent():
    blocks = markdown_to_blockkit("- a\n- b\n    - nested")
    rt = _first(blocks, "rich_text")
    lists = [e for e in rt["elements"] if e["type"] == "rich_text_list"]
    assert any(l["style"] == "bullet" and l["indent"] == 0 for l in lists)
    assert any(l["indent"] == 1 for l in lists)  # nested level


def test_ordered_list_style():
    blocks = markdown_to_blockkit("1. one\n2. two")
    rt = _first(blocks, "rich_text")
    lst = next(e for e in rt["elements"] if e["type"] == "rich_text_list")
    assert lst["style"] == "ordered"
    assert len(lst["elements"]) == 2


def test_blockquote_and_codeblock():
    blocks = markdown_to_blockkit("> quoted\n\n```\ncode\n```")
    rt = _first(blocks, "rich_text")
    kinds = [e["type"] for e in rt["elements"]]
    assert "rich_text_quote" in kinds
    assert "rich_text_preformatted" in kinds


def test_heading_becomes_header_block():
    blocks = markdown_to_blockkit("# Title\n\nbody")
    header = _first(blocks, "header")
    assert header["text"]["type"] == "plain_text"
    assert header["text"]["text"] == "Title"


def test_emoji_leaf():
    blocks = markdown_to_blockkit("nice :tada: day")
    leaves = _first(blocks, "rich_text")["elements"][0]["elements"]
    assert any(l["type"] == "emoji" and l["name"] == "tada" for l in leaves)


def test_hr_becomes_divider():
    blocks = markdown_to_blockkit("a\n\n---\n\nb")
    assert any(b["type"] == "divider" for b in blocks)
