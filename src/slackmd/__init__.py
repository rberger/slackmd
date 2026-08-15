"""slackmd: Slack <-> Markdown conversion.

The public surface is the pure conversion core. Clipboard and Slack I/O live in
adapters (`slackmd.cli`, future `slackmd.slack`) and are guarded; see SAFETY.md.
"""

from .core import (
    markdown_to_blockkit,
    markdown_to_mrkdwn,
    mrkdwn_to_markdown,
    slack_html_to_markdown,
)

__all__ = [
    "slack_html_to_markdown",
    "mrkdwn_to_markdown",
    "markdown_to_mrkdwn",
    "markdown_to_blockkit",
]

__version__ = "0.0.1"
