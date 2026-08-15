"""Phase 1 converter tests. Synthetic HTML only, safe to commit and run anywhere."""

from slackmd import slack_html_to_markdown


def test_bold_italic_inline_code():
    out = slack_html_to_markdown("<b>Bold</b> and <i>ital</i> and <code>x = 1</code>")
    assert "**Bold**" in out
    assert "*ital*" in out
    assert "`x = 1`" in out


def test_bullets_and_emoji_shortcode():
    html = (
        '<ul><li>one <img data-stringify-emoji=":white_check_mark:" '
        'alt=":white_check_mark:"></li><li>two</li></ul>'
    )
    out = slack_html_to_markdown(html)
    assert "- one :white_check_mark:" in out
    assert "- two" in out
    # emoji shortcode must not be backslash-escaped
    assert ":white\\_check\\_mark:" not in out


def test_author_header_stripped_by_default():
    html = "<div>Jane Doe  [4:38 PM]</div><div>Hello world</div>"
    out = slack_html_to_markdown(html)
    assert "[4:38 PM]" not in out
    assert "Hello world" in out


def test_author_header_kept_when_requested():
    html = "<div>Jane Doe  [4:38 PM]</div><div>Hello world</div>"
    out = slack_html_to_markdown(html, include_author_header=True)
    assert "[4:38 PM]" in out
