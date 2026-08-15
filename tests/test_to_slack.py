"""markdown_to_mrkdwn (reverse direction) tests. Synthetic, safe to commit."""

from slackmd import markdown_to_html, markdown_to_mrkdwn


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


def test_markdown_to_html_for_paste():
    html = markdown_to_html("# T\n\n**b** [x](https://y.io)\n\n- a\n- b")
    assert "<h1>" in html
    assert "<strong>b</strong>" in html
    assert '<a href="https://y.io">x</a>' in html
    assert "<ul>" in html and "<li>a</li>" in html


def test_html_multiline_blockquote_splits_into_paragraphs():
    html = markdown_to_html("> a quoted line\n> a second **bold** line")
    # Slack collapses <br> in quotes, so each line becomes its own <p> (no <br>),
    # and inline markup within a line is preserved.
    assert "<br" not in html
    assert "<p>a quoted line</p>" in html
    assert "<p>a second <strong>bold</strong> line</p>" in html
    assert html.count("<blockquote>") == 1


def test_html_singleline_blockquote_unchanged():
    html = markdown_to_html("> just one line")
    assert "<blockquote>" in html and "just one line" in html
