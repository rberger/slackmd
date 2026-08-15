"""Slack post payload tests. Pure (no network), safe to commit and run in the sandbox."""

from slackmd.slack import build_message


def test_build_message_shape():
    payload = build_message("# Title\n\n- a\n- b", "C0123ABCD")
    assert payload["channel"] == "C0123ABCD"
    assert isinstance(payload["blocks"], list)
    assert payload["blocks"][0]["type"] == "header"
    assert isinstance(payload["text"], str) and "Title" in payload["text"]


def test_build_message_custom_fallback():
    payload = build_message("**hi**", "C1", text="custom fallback")
    assert payload["text"] == "custom fallback"
