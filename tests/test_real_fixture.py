"""Quality check against the private real Slack capture.

Skips automatically when the gitignored sample is absent (e.g. in CI or the Docker
sandbox), so it never blocks a clean environment and never leaks Informed content.
"""

import pathlib

import pytest

from slackmd import slack_html_to_markdown

_FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "samples" / "frustrating-01.html"


@pytest.mark.skipif(not _FIXTURE.exists(), reason="private local fixture not present")
def test_real_fixture_quality():
    out = slack_html_to_markdown(_FIXTURE.read_text())
    # bold pseudo-heading preserved
    assert "**Bi-directional replication required:**" in out
    # emoji recovered as a clean, unescaped shortcode
    assert ":white_check_mark:" in out
    assert ":white\\_check\\_mark:" not in out
    # author/timestamp header stripped by default
    assert "[4:38 PM]" not in out
    # inline code preserved
    assert "`configs/`" in out
