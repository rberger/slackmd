"""Cross-source consistency on the real AWS-seminar captures.

All three rich sources of the SAME message (public.html from select+copy,
text/markdown and slack/texty from Copy message) should converge on the same
content. Skips when the local samples are absent (CI / sandbox), so it never leaks
and never blocks a clean environment.
"""

import pathlib

import pytest

from slackmd import clean_slack_markdown, quill_to_markdown, slack_html_to_markdown

_S = pathlib.Path(__file__).resolve().parents[1] / "samples"
_HTML = _S / "aws-seminar.html"
_MD = _S / "aws-seminar.md"
_QUILL = _S / "aws-seminar.quill.json"

_URLS = [
    "aws-experience.com/amer/smb/e/525d0/",  # Build Autonomous Coding Agents
    "aws-experience.com/amer/smb/e/525ff/",  # Edge-Bytes CloudFront/WAF
    "aws-experience.com/amer/smb/e/f3913/",  # AWS Transform
    "aws-experience.com/amer/smb/e/bce51/",  # AWS DevOps Agent
]
_BULLETS = [
    "Connect source code repositories",
    "Triage findings by severity",
    "How to onboard and discover repositories",
]


@pytest.mark.skipif(
    not (_HTML.exists() and _MD.exists() and _QUILL.exists()),
    reason="private local captures not present",
)
def test_all_sources_agree_on_content():
    outputs = {
        "html": slack_html_to_markdown(_HTML.read_text()),
        "markdown": clean_slack_markdown(_MD.read_text()),
        "quill": quill_to_markdown(_QUILL.read_text()),
    }
    for name, md in outputs.items():
        for url in _URLS:
            assert url in md, f"{name}: missing {url}"
        for bullet in _BULLETS:
            assert bullet in md, f"{name}: missing bullet {bullet!r}"
        # no leftover Slack over-escaping
        assert "\\(" not in md and "\\)" not in md, f"{name}: stray escape"
