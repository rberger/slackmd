"""slackmd: Slack <-> Markdown conversion.

The public surface is the pure conversion core plus the source router. Clipboard and
Slack I/O live in adapters (`slackmd.cli`) and are guarded; see SAFETY.md.
"""

from .core import (
    clean_slack_markdown,
    markdown_to_blockkit,
    markdown_to_html,
    markdown_to_mrkdwn,
    mrkdwn_to_markdown,
    quill_to_markdown,
    slack_html_to_markdown,
)
from .sources import Conversion, parse_chromium_custom_data, route

__all__ = [
    "slack_html_to_markdown",
    "clean_slack_markdown",
    "quill_to_markdown",
    "mrkdwn_to_markdown",
    "markdown_to_mrkdwn",
    "markdown_to_html",
    "markdown_to_blockkit",
    "route",
    "parse_chromium_custom_data",
    "Conversion",
]

__version__ = "0.0.1"
