# Eval corpus

Golden-file conversion cases. Layout (see docs/SPEC.md section 7):

```
evals/cases/<feature>/
    input.html | input.md | input.mrkdwn
    expected.md | expected.mrkdwn
```

Runner is `pytest` (parametrized over the corpus) with a `--report` fidelity matrix
and a `--min-accuracy` gate. All cases are pure string-in / string-out, so they run
in the network-isolated sandbox with no macOS or Slack access.

Golden fixtures under `cases/` should be captured from REAL copied Slack messages
(Phase 0 output) so the corpus reflects the HTML Slack actually emits.
