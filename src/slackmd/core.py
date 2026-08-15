"""Pure conversion core.

No macOS APIs, no filesystem, no network live in this module. Everything here is a
pure function of its input string, which is what makes it safe to run anywhere
(including the network-isolated Docker sandbox) and trivial to eval. See SAFETY.md.
"""

from __future__ import annotations


def slack_html_to_markdown(html: str) -> str:
    """Convert Slack's clipboard ``public.html`` into CommonMark.

    PRIMARY path (Phase 1). Lossy edges: @mentions arrive as display names, custom
    emoji as shortcodes only. See docs/SPEC.md section 5.
    """
    raise NotImplementedError("Phase 1")


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
