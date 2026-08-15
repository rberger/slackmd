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

### macOS hotkeys (Quick Actions)

Install two Services and pre-bind the default global shortcuts:

```bash
bash macos/quick-actions/install.sh
```

Default shortcuts (set best-effort by the installer):

| Shortcut | Service | Action |
|----------|---------|--------|
| `⌥⌘S` (Cmd+Option+S) | slackmd: Slack to Markdown | `from-slack --copy` |
| `⌥⌘M` (Cmd+Option+M) | slackmd: Markdown to Slack | `to-slack --copy` |

macOS treats Services shortcuts as user preferences, so the pre-bind may need a logout
to activate, and an app-level shortcut can shadow it. If a shortcut is not active, set
or change it in System Settings > Keyboard > Keyboard Shortcuts > Services > General.
First run may prompt to allow pasteboard access; allow it.

Daily loop: copy in Slack, press `⌥⌘S`, paste into your agent; copy Markdown, press
`⌥⌘M`, paste into Slack.

## Layout

```
src/slackmd/core.py   pure conversion functions (no I/O)  <- safe to run anywhere
src/slackmd/cli.py    thin CLI + macOS clipboard adapter  <- only touches pasteboard
evals/                golden-file conversion corpus
docs/SPEC.md          the plan
```

Status: both directions built and validated against real Slack (Slack HTML/Quill/text
to Markdown, and Markdown to Slack via HTML paste), with macOS hotkeys. Block Kit API
posting is the remaining optional phase. See [`docs/SPEC.md`](docs/SPEC.md) section 2.5.
