# slackmd

Convert a copied Slack message into clean Markdown for feeding to Kiro or other
agents, and (bonus) convert full Markdown into properly formatted Slack output.

- Full design, fidelity matrix, phased plan, and eval design: [`docs/SPEC.md`](docs/SPEC.md)
- Isolation and safety model: [`SAFETY.md`](SAFETY.md)

## Quick start

```bash
make setup     # isolated venv (uv), Python 3.13, incl. macOS clipboard extra
make test      # unit tests
make sandbox   # run the pure core + evals in a Docker container with NO network
```

## Layout

```
src/slackmd/core.py   pure conversion functions (no I/O)  <- safe to run anywhere
src/slackmd/cli.py    thin CLI + macOS clipboard adapter  <- only touches pasteboard
evals/                golden-file conversion corpus
docs/SPEC.md          the plan
```

Status: scaffolding. Phase 1 (Slack HTML -> Markdown) is the first tracer bullet.
