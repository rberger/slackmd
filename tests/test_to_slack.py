"""markdown_to_mrkdwn (reverse direction) tests. Synthetic, safe to commit."""

from slackmd import markdown_to_mrkdwn


def test_inline_emphasis_mapping():
    out = markdown_to_mrkdwn("**bold** _ital_ ~~strike~~ `code`")
    # CommonMark ** -> Slack *, _/* -> _, ~~ -> ~
    assert "*bold*" in out
    assert "_ital_" in out
    assert "~strike~" in out
    assert "`code`" in out


def test_heading_becomes_bold_line():
    assert markdown_to_mrkdwn("# Title") == "*Title*"
    assert markdown_to_mrkdwn("### Sub heading") == "*Sub heading*"


def test_link_mapping():
    assert markdown_to_mrkdwn("[Kiro](https://kiro.dev)") == "<https://kiro.dev|Kiro>"


def test_bullets_and_nesting():
    md = "- one\n- two\n    - nested"
    out = markdown_to_mrkdwn(md)
    assert "• one" in out
    assert "• two" in out
    assert "    • nested" in out


def test_ordered_list():
    out = markdown_to_mrkdwn("1. first\n2. second")
    assert "1. first" in out
    assert "2. second" in out


def test_blockquote_single_level():
    out = markdown_to_mrkdwn("> quoted line")
    assert out == "> quoted line"


def test_code_fence_drops_language():
    out = markdown_to_mrkdwn("```python\nx = 1\n```")
    assert out == "```\nx = 1\n```"


def test_entity_escaping_default_on():
    out = markdown_to_mrkdwn("if x < y & y > z")
    assert "&lt;" in out and "&gt;" in out and "&amp;" in out


def test_no_escape_flag():
    out = markdown_to_mrkdwn("if x < y & y > z", escape=False)
    assert "< y" in out and "&amp;" not in out


def test_table_becomes_monospace_block():
    md = "| a | b |\n| - | - |\n| 1 | 22 |"
    out = markdown_to_mrkdwn(md)
    assert out.startswith("```") and out.endswith("```")
    assert "a" in out and "22" in out
