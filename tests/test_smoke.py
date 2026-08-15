"""Smoke test: proves the isolated env + import path work.

Runs in the Docker sandbox with no network access, confirming the core imports and
touches nothing outside the process.
"""

import slackmd


def test_package_exposes_core():
    for name in (
        "slack_html_to_markdown",
        "mrkdwn_to_markdown",
        "markdown_to_mrkdwn",
        "markdown_to_blockkit",
    ):
        assert callable(getattr(slackmd, name))


def test_core_deps_import():
    # The two pure-core dependencies must be importable in the sandbox.
    import markdown_it  # noqa: F401
    import markdownify  # noqa: F401
