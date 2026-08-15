# Safety and isolation model

The concern: run code freely without damaging your system or anything in the cloud.
This project is structured so that the risky surfaces are small, opt-in, and guarded.

## Where the risk actually is

This project needs no AWS or cloud resources at all. There are exactly two surfaces
that touch anything outside the process:

1. The macOS clipboard (read the copied Slack HTML, write Markdown back). This only
   touches the pasteboard, which is transient and reversible. It never writes files.
2. The Slack API (reverse direction: post a message). This is the only cloud
   mutation vector, and it is guarded (see below).

Everything else, the actual conversion, is pure string-in / string-out.

## The four layers

1. Pure core (`src/slackmd/core.py`): no macOS APIs, no filesystem, no network. Safe
   to run anywhere. All evals target this layer.
2. Docker sandbox (`make sandbox`): builds an image with ONLY the pure core (no
   `macos` or `slack` extras) and runs it with `--network none`. Nothing in this
   image can read your pasteboard or reach the network/cloud. This is where code
   runs freely during development.
3. macOS clipboard adapter (`src/slackmd/cli.py`): the only code that touches the
   pasteboard. Reversible, file-system-free.
4. Slack adapter (future, `slack` extra): DRY-RUN BY DEFAULT. Posting requires an
   explicit `--post` flag plus a channel allowlist. Recommended posture: use a
   dedicated throwaway/test Slack workspace or a private test channel, never a real
   shared channel, until the conversion is trusted.

## Credential handling

- Slack tokens are read from an environment variable only, never committed. `.env`
  and `*.token` are gitignored.
- No token is required for the primary Slack -> Markdown clipboard path.

## Agent operating constraints (backstop)

The KiroCrew agent runs under a safety policy: no destructive shell commands, no
destructive cloud operations, no reading of credential files. The sandbox and the
dry-run-by-default Slack adapter are the project-level belt to that suspenders.
