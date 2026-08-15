# slackmd

Convert a copied Slack message into clean Markdown for feeding to Kiro or other
agents, and (bonus) convert full Markdown into properly formatted Slack output.

- Full design, fidelity matrix, phased plan, and eval design: [`docs/SPEC.md`](docs/SPEC.md)
- Isolation and safety model: [`SAFETY.md`](SAFETY.md)

## Requirements

- macOS (the tool reads and writes the native pasteboard).
- [`uv`](https://docs.astral.sh/uv/): `brew install uv`, or
  `curl -LsSf https://astral.sh/uv/install.sh | sh`. `uv` manages the Python (3.13) and
  the virtualenv for you, so no separate Python install is needed.
- Optional: Docker Desktop, only if you want to run `make sandbox`.

## Install

```bash
git clone git@github.com:rberger/slackmd.git
cd slackmd
make setup     # creates an isolated venv (uv, Python 3.13) with the macOS clipboard extra
```

Run the CLI with `uv run` from the repo directory:

```bash
uv run slackmd from-slack --copy
```

Or install it as a global `slackmd` command so it works from any directory:

```bash
uv tool install ".[macos]"
```

The usage examples below are written as `slackmd ...`; if you did not install it
globally, prefix them with `uv run` and run from the repo directory.

## Develop

```bash
make test      # unit tests
make sandbox   # run the pure core + evals in a Docker container with NO network
```

## Usage

Two directions, both driven off the clipboard. The CLI reads and writes the macOS
pasteboard itself, so you just copy, run, and paste.

### Slack to Markdown

Copy a Slack message (either "Copy message" from the hover menu, or select the text
and Cmd-C), then:

```bash
slackmd from-slack --copy     # clipboard Slack content -> Markdown, back on clipboard
```

Paste the Markdown into Kiro or any agent prompt. The converter auto-detects the best
source Slack put on the clipboard and routes by fidelity: `text/markdown` > Quill
(`slack/texty`) > `public.html` > plain text. `--keep-author` keeps the leading
"Name [time]" line (stripped by default).

### Markdown to Slack

Copy some Markdown, then:

```bash
slackmd to-slack --copy       # clipboard Markdown -> rich HTML (+ mrkdwn) on clipboard
```

Paste into a Slack message box. Slack's composer imports the HTML as native formatting
(bold, italic, links, nested/ordered lists, quotes, code blocks). Pasting plain
`mrkdwn` does not work in the WYSIWYG composer, which is why the HTML flavor is written.

### Post to Slack (Block Kit)

For programmatic posting instead of pasting, convert Markdown to Block Kit and post via
the Slack API:

```bash
slackmd to-blockkit                    # clipboard Markdown -> Block Kit blocks JSON (stdout)
slackmd post --channel C0XXXX          # dry-run: prints the chat.postMessage payload
slackmd post --channel C0XXXX --send   # actually posts (needs SLACK_BOT_TOKEN)
```

`post` is dry-run by default. `--send` reads `SLACK_BOT_TOKEN` from the environment (a
classic bot-token app with `chat:write`) and honors an optional `SLACK_ALLOWED_CHANNELS`
allowlist. Block Kit `rich_text` preserves nested/ordered lists, quotes, code blocks,
links, and emoji, validated live against `chat.postMessage`. See [`SAFETY.md`](SAFETY.md).

### macOS hotkeys (Quick Actions)

Install two Services and pre-bind the default global shortcuts:

```bash
bash macos/quick-actions/install.sh
```

Default shortcuts (set best-effort by the installer):

| Shortcut | Service | Action |
|----------|---------|--------|
| `⌥⌘S` (Cmd+Option+S) | slackmd: Slack to Markdown | `from-slack --copy` |
| `⌃⌥⌘M` (Ctrl+Cmd+Option+M) | slackmd: Markdown to Slack | `to-slack --copy` |

Each service transforms the clipboard and signals with a sound plus a notification; it
does not paste for you. Copy, press the shortcut, then paste (`⌘V`) into the target app.
The Markdown→Slack shortcut uses Control (`⌃⌥⌘M`) because plain `⌘M` / `⌥⌘M` is macOS
"minimize" and would minimize the window instead.

These are no-input services (they read the clipboard themselves), so they appear in the
application Services menu and on the hotkeys, not in the right-click text-selection menu.

macOS treats Services shortcuts as user preferences, so the pre-bind may need a logout
to activate, and an app-level shortcut can shadow it. If a shortcut is not active, set
or change it in System Settings > Keyboard > Keyboard Shortcuts > Services > General.
First run may prompt to allow pasteboard access; allow it.

Daily loop: copy in Slack, press `⌥⌘S`, then `⌘V` into your agent; copy Markdown, press
`⌃⌥⌘M`, then `⌘V` into Slack.

## Layout

```
src/slackmd/core.py     pure conversion functions (no I/O)  <- safe to run anywhere
src/slackmd/sources.py  clipboard source detection + fidelity router (pure)
src/slackmd/cli.py      thin CLI + macOS clipboard adapter  <- only touches pasteboard
src/slackmd/slack.py    Slack API poster (chat.postMessage, dry-run by default)
evals/                  golden-file conversion corpus
docs/SPEC.md            the plan
```

Status: complete. Both clipboard directions validated against real Slack (Slack
HTML/Quill/text to Markdown, and Markdown to Slack via HTML paste), plus Block Kit
posting via `chat.postMessage` (validated live), with macOS hotkeys. The optional
`SlackEnricher` for canonical @mentions and custom emoji is the one remaining item.
See [`docs/SPEC.md`](docs/SPEC.md).
