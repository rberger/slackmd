"""Golden-file corpus runner.

Each case dir under evals/cases/<name>/ holds an `input.html` (a real Slack
`public.html` capture) and the `expected.md` our converter should produce. Pure
string-in / string-out, so it runs in the network-isolated sandbox with no macOS or
Slack access. Add a case by dropping in a new dir; it is picked up automatically.
"""

import pathlib

import pytest

from slackmd import slack_html_to_markdown

_CASES_DIR = pathlib.Path(__file__).resolve().parent / "cases"


def _html_cases():
    return sorted(p.parent.name for p in _CASES_DIR.glob("*/input.html"))


@pytest.mark.parametrize("case", _html_cases())
def test_html_to_markdown_golden(case):
    case_dir = _CASES_DIR / case
    html = (case_dir / "input.html").read_text()
    expected = (case_dir / "expected.md").read_text()
    assert slack_html_to_markdown(html) + "\n" == expected
