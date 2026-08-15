# Slack ↔ Markdown Bridge: Plan, Spec, and Eval Design

Working name: `slackmd`. A macOS clipboard tool (plus optional Slack-app layer) that converts a
copied Slack message into clean Markdown for feeding to Kiro or other agents, and (bonus)
converts full Markdown into properly formatted Slack output.

Status: v2. Both directions built and validated against real Slack (see section 2.5).
The original research assumptions in 2.1 to 2.4 are preserved; 2.5 records where the build
confirmed or corrected them.

---

## 1. Goal

Primary: copy a Slack message, get faithful Markdown on the clipboard, ready to paste into an
agent prompt.

Bonus (reverse): take arbitrary Markdown and produce Slack-correct output, either as `mrkdwn`
text to paste into the composer, or posted directly into a channel via the Slack API.

Constraints from the environment:
- Rob prefers Python or Rust. Recommendation below is Python core, for reasons that are about
  library maturity, not preference.
- Free personal Slack workspace `ibd` cannot use the next-gen (Deno) Slack platform, but classic
  granular-scope apps with a bot token are fully supported. That matters only for the reverse
  direction and the optional API-enrichment path.

---

## 2. Findings that shape the design

These come from the three research passes and are the load-bearing facts.

### 2.1 What is actually on the clipboard when you Cmd-C a Slack message

- The macOS pasteboard gets `public.html` (Slack's rendered HTML, tagged with `data-stringify-*`
  attributes) and `public.utf8-plain-text` (already-rendered plain text, NOT `mrkdwn`).
- The plain-text flavor is lossy: bold arrives as the literal words, a code block arrives as its
  contents with blank lines dropped. So the plain-text flavor is not a usable source.
- The `public.html` flavor is the only structurally faithful source on the clipboard. It is the
  right transport for the primary direction.
- RTF is not reliably present (Electron/Chromium does not synthesize it). Do not depend on it.
- Clipboard HTML is lossy at two specific edges: `@mentions` arrive as display names, not the
  canonical `<@U012...>` IDs, and custom emoji arrive as `<img>` with the `:shortcode:` in an
  attribute, not as a portable image. Standard emoji come through as Unicode. Threads,
  reactions, author, timestamp, and permalink are not on the clipboard at all.

Implication: clipboard-HTML gives excellent formatting fidelity but cannot reconstruct working
mentions or custom-emoji images. To recover those you need the Slack API (see 2.3).

### 2.2 Slack `mrkdwn` is a lossy dialect, in both directions

- `mrkdwn` inverts CommonMark emphasis: single `*` is bold in Slack, italic in CommonMark. This
  is the number-one conversion bug source.
- Slack has no headings, no tables, single-level blockquotes only, and no real list syntax via
  the API (you emit literal `•` glyphs and literal numbers; the composer auto-formats but the API
  does not).
- Only `& < >` are control characters that must be entity-escaped in `mrkdwn`; nothing else.
- The high-fidelity structural target is Block Kit `rich_text` JSON (what Slack's own WYSIWYG
  composer emits). It is the only way to get real ordered/nested lists, and it carries canonical
  entity leaves (user, channel, usergroup, link, emoji). `mrkdwn` strings are the low-fidelity,
  paste-friendly target.

### 2.3 Libraries: reuse where mature, hand-roll the reverse direction

- md → Slack `mrkdwn` (Python): `fla9ua/markdown_to_mrkdwn` is the most mature pure-Python option
  (zero deps, plugin hooks) but is regex/line-based. The robust path is an AST engine
  (`markdown-it-py`) with a custom renderer.
- md → Block Kit JSON: `tryfabric/mack` (JS) is the reference algorithm; Python analogs exist but
  are thinner.
- slack `mrkdwn` → CommonMark (reverse): no mature library in any language. Slack documents the
  exact retrieval grammar, so a focused ~200-line tokenizer is more reliable than bending a
  general parser.
- Clipboard access: Python via PyObjC (`pyobjc-framework-Cocoa`, read arbitrary UTIs with
  `NSPasteboard.stringForType_` / `dataForType_`) or the `pasteboard` wheel for common flavors.
  Rust would need `clipboard-rs` for HTML reads (`arboard` is write-only for HTML), which is why
  Python is the lower-friction core.

### 2.4 Delivery on macOS

- The tool is fundamentally `pbpaste | transform | pbcopy`. A macOS Shortcuts / Automator Quick
  Action bound to a global keyboard shortcut delivers that with zero permission prompts, zero
  signing, and no background process. The OS hands you the hotkey, so you skip the Accessibility
  (TCC) minefield that a self-rolled global event tap (rumps + pynput) walks into.
- Hammerspoon is the strong secondary: most reliable global hotkeys, Accessibility granted once
  to a pre-notarized app, trivial to add multiple per-direction hotkeys.
- A menu-bar app (rumps or Rust tray) is only worth the signing/TCC cost if this becomes a
  distributed product with its own UI.
- For the reverse direction, a Slack slash-command app is the wrong tool (it inverts the
  workflow and needs an always-on socket daemon). If we post to Slack, the CLI should hold a
  classic bot token and call `chat.postMessage` directly (no Socket Mode, no daemon).

### 2.5 Verified findings from the build (2026-08-14)

**The copy method determines the source.** The 2.1 assumption (only `public.html`) was
incomplete. Slack puts different flavors on the pasteboard depending on how you copy:

- **Select the message text and Cmd-C** yields `public.html` (Slack's rendered DOM). This
  build's Slack emits clean semantic tags (`b`, `i`, `ul`, `li`, `code`, emoji
  `<img alt=":shortcode:">`) with no `data-stringify-*` wrappers, so the pre-cleaner is simpler
  than 2.1 assumed.
- **The "Copy message" hover action (⌘C)** yields NO `public.html`. Instead Slack packs two rich
  flavors into Chromium's `org.chromium.web-custom-data` blob: `text/markdown` (Slack's own
  near-CommonMark; it only over-escapes `\(` `\)`) and `slack/texty` (a Quill Delta with explicit
  `bold`/`italic`/`link` inline attributes and `list`/`blockquote` block attributes on the
  terminating newline). The `public.utf8-plain-text` flavor is rendered text, not usable.

**Multi-source router (implemented).** `slackmd from-slack` gathers every available flavor and
routes by fidelity: `text/markdown` > `slack/texty` (Quill) > `public.html` > `text/plain`. All
three rich sources of the same message were verified to converge on the same content. The
`web-custom-data` blob is a `base::Pickle`; `parse_chromium_custom_data` decodes it (pure, so it
runs in the sandbox).

**HTML paste is the reverse-direction transport (verified).** Pasting plain `mrkdwn` into Slack's
WYSIWYG composer renders literally (asterisks, underscores, and `>` all shown as text; only bare
URLs auto-link). The working path is symmetric to the read side: write `public.html` to the
clipboard and Slack's composer imports it as native formatting (bold, italic, strike, inline
code, links, nested/ordered lists, blockquote, code block). `slackmd to-slack --copy` writes
`public.html` (from `markdown_to_html`, with `breaks=True` so multi-line quotes keep their line
breaks) plus a `mrkdwn` plain-text fallback. `mrkdwn` text remains the target for API posting,
not for pasting.

**Fidelity notes.**
- Our HTML to Markdown output matched Slack's own `text/markdown` for the same message, and was
  cleaner: no over-escaped parens, and correct emphasis boundaries where Slack emitted an
  ambiguous `*****` run.
- A line's bold-ness in Slack's live UI can differ from the copied HTML in either direction; the
  clipboard HTML is authoritative for what we can convert. Recovering render-only styling would
  need the API path.

**Block Kit posting (verified live).** `chat.postMessage` with `markdown_to_blockkit` output was
validated on a real (paid Informed) workspace: styled inline text, links, emoji, nested bullets,
numbered ordered lists, a multi-line quote, and a code block all render correctly. One Slack
rendering quirk: consecutive `rich_text_list` blocks are merged into a single run that adopts the
first list's markers, so a bullet list directly followed by an ordered list showed all bullets.
The fix is to emit an empty `rich_text_section` between adjacent top-level lists (never inside a
nested list), which keeps the ordered list numbered; confirmed live.

---

## 3. Proposed architecture

Three layers, cleanly separated so the core is testable without macOS or Slack.

```
┌─────────────────────────────────────────────────────────────┐
│  Delivery layer (macOS)                                       │
│  Quick Action / Hammerspoon hotkey  →  runs the CLI           │
└───────────────┬───────────────────────────────────────────────┘
                │ pbpaste / pbcopy (clipboard I/O)
┌───────────────▼───────────────────────────────────────────────┐
│  CLI layer  (slackmd)                                          │
│    from-slack   clipboard(html) → markdown → clipboard         │
│    to-slack     clipboard(markdown) → mrkdwn → clipboard       │
│    post         markdown → Block Kit → chat.postMessage  (opt) │
└───────────────┬───────────────────────────────────────────────┘
                │ pure functions, no I/O
┌───────────────▼───────────────────────────────────────────────┐
│  Core library  (pure, unit-testable, no macOS/Slack deps)      │
│    slack_html_to_markdown(html)      → str   (PRIMARY)         │
│    mrkdwn_to_markdown(text)          → str   (API path)        │
│    markdown_to_mrkdwn(md)            → str   (paste target)    │
│    markdown_to_blockkit(md)          → list  (API target)      │
│    (optional) SlackEnricher: resolve @display→<@Uid>, emoji    │
└─────────────────────────────────────────────────────────────┘
```

- Core library has no macOS or network dependency, so evals run anywhere (CI-friendly).
- Clipboard and Slack I/O live only in thin adapters, mirroring the tc separation Rob already
  knows.

### Engine choices
- CommonMark parsing: `markdown-it-py` (spec-compliant, token stream, GFM plugins).
- HTML → Markdown (primary path): a converter (`markdownify`) fronted by a Slack-HTML
  pre-cleaner that normalizes the `data-stringify-*` spans and preserves code-block blank lines.
- Reverse `mrkdwn` → CommonMark: hand-rolled tokenizer over Slack's documented `<...>` grammar.
- Clipboard: PyObjC `NSPasteboard` (read `public.html`, write `public.utf8-plain-text`).

---

## 4. Component spec

### 4.1 `slack_html_to_markdown(html: str) -> str`  (primary)
1. Parse the Slack HTML.
2. Pre-clean: collapse `data-stringify-type="paragraph-break"` and line-break spans into real
   newlines; unwrap Slack code-block spans into fenced blocks preserving blank lines; convert
   emoji `<img>` back to `:shortcode:` from the alt/data attribute.
3. Convert to CommonMark via `markdownify` with a Slack-tuned ruleset.
4. Post-normalize: strip trailing whitespace, collapse >2 blank lines, keep `@displayname` as
   plain `@displayname` text (mentions are lossy without the API).

### 4.2 `mrkdwn_to_markdown(text: str) -> str`  (API / paste-back path)
Tokenizer over the Slack grammar: unescape `&amp; &lt; &gt;`, invert `*bold*`→`**bold**` and
`_italic_`→`*italic*`, `~s~`→`~~s~~`, rewrite `<url|label>`→`[label](url)` and bare `<url>`→
`<url>`, map `<@U…>`/`<#C…|name>`/`<!subteam^…>`/`<!here|channel|everyone>` to readable text,
leave `:emoji:` as-is. Single-level blockquote and code fences pass through.

### 4.3 `markdown_to_mrkdwn(md: str) -> str`  (bonus, paste target)
Walk the `markdown-it-py` AST and render `mrkdwn`, applying the documented degradations:
headings → `*bold*` line, tables → aligned monospace block, images → alt text (+ note), nested
lists → flattened with `•`/literal numbers, links → `<url|label>`, task lists → `☐`/`☑`. Escape
`& < >`.

### 4.4 `markdown_to_blockkit(md: str) -> list[dict]`  (bonus, high-fidelity API target)
Same AST, render Block Kit `rich_text` (+ `header`, `divider`, `image`, `section.fields` for
tables). This is the path that preserves real ordered/nested lists and canonical entities.

### 4.5 Optional `SlackEnricher`  (fidelity upgrade, needs a bot token)
Given a message permalink (Slack "Copy link"), resolve channel + ts, call
`conversations.history`/`replies` to fetch canonical `text`/`blocks`, and restore working
`@mentions`, channel links, and custom-emoji shortcodes that the clipboard cannot. This is the
difference between "reads nicely" and "round-trips back into Slack as working pings".

---

## 5. Fidelity matrix

| Feature | Slack→MD via clipboard HTML | Slack→MD via API | MD→`mrkdwn` | MD→Block Kit |
|---|---|---|---|---|
| bold / italic / strike / inline code | full | full | full (emphasis inverted) | full |
| code block | full (HTML preserves blanks) | full | full | full |
| blockquote | full | full | single-level | single-level |
| ordered / nested lists | good | good | flattened, literal numbers | full (rich_text) |
| links | full | full | full | full |
| `@mentions` | display name only (lossy) | canonical, working | pass-through | canonical entity |
| channel refs | name only | canonical | pass-through | canonical entity |
| custom emoji | `:shortcode:` text only | shortcode + resolvable | pass-through | emoji leaf |
| headings | n/a (source has none) | n/a | → bold line | header block |
| tables | n/a | n/a | → monospace block | section.fields |
| images | alt text only | url available | alt text | image block |
| thread / reactions / metadata | not on clipboard | available via API | n/a | n/a |

---

## 6. Phased plan (tracer bullets)

- **Phase 0, spike (0.5 day):** [DONE] confirmed the pasteboard reality on Rob's Slack build.
  Discovered the copy-method / source split in 2.5.
- **Phase 1, tracer bullet (primary, end to end):** [DONE] `slack_html_to_markdown` + `from-slack`
  CLI. Validated against a real rich message and a committed golden case; multi-source router
  added (2.5). Quick Action hotkey still to do.
- **Phase 2, harden Slack→MD:** [PARTIAL] auto-discovering golden-file corpus + cross-source
  consistency test in place. Mention/custom-emoji API enrichment still open.
- **Phase 3, reverse direction (bonus, paste):** [DONE] `markdown_to_mrkdwn` + `markdown_to_html`
  + `to-slack` CLI. HTML paste path verified in Slack. The Markdown→Slack Quick Action
  (`⌃⌥⌘M`) converts and auto-pastes (`⌘V` via System Events, Accessibility permission);
  Slack→Markdown (`⌥⌘S`) copies for manual paste into the agent.
- **Phase 4, high-fidelity Slack integration (optional):** [DONE] `markdown_to_blockkit`
  (Block Kit `rich_text`) + `to-blockkit` and a dry-run-by-default `post` command
  (`chat.postMessage`, stdlib urllib, env token, channel allowlist). Validated live on a
  real workspace: styled inline text, links, emoji, nested bullets, numbered ordered
  lists, multi-line quote, and code block all render. The `SlackEnricher` for canonical
  `@mentions`/custom emoji remains the one open item.

Each phase is independently useful and independently testable.

---

## 7. Eval design

Same shape as the tc eval harness: a golden corpus with a pass/fail gate and a per-feature
fidelity report, runnable in CI with no macOS or network.

- **Layout:** `evals/cases/<feature>/{input.html|input.md|input.mrkdwn, expected.md|expected.mrkdwn}`.
- **Runner:** `pytest` parametrized over the corpus, plus a `--report` mode that prints a
  feature-by-feature pass matrix and an overall accuracy score gated by `--min-accuracy`.
- **Case families:**
  1. Slack HTML → MD, one case per formatting feature (bold, italic, strike, inline code, code
     block with blank lines, blockquote, ordered/unordered/nested lists, labeled/bare links,
     mentions, channel refs, standard + custom emoji).
  2. MD → `mrkdwn`, one case per feature including the lossy ones (assert graceful degradation,
     e.g. heading becomes a bold line, table becomes a monospace block).
  3. Round-trip: `md → mrkdwn → md` stable over the supported subset; `slack_html → md` stable
     under re-conversion.
  4. Escaping: `& < >` and code containing `if (x < y)` survive intact.
  5. Adversarial: emphasis-inversion traps, nested emphasis inside links, mixed emoji forms.
- **Golden fixtures:** captured from real copied Slack messages (Phase 0 output) so the corpus
  reflects the actual HTML Slack emits, not a guess.

---

## 8. Open decisions (need Rob's call)

1. **Transport for the primary direction.** Clipboard-HTML only (zero setup, mentions/custom
   emoji are lossy) vs. also build the API enrichment path (needs a classic bot token, restores
   working mentions and emoji). Recommendation: ship Phase 1 clipboard-only, add enrichment in
   Phase 4 only if the lossy mentions actually bite.
2. **Reverse-direction target.** `mrkdwn` text to paste into the composer (simple, lossy) vs.
   post via `chat.postMessage` with Block Kit (high fidelity, needs a token). Or both.
3. **Delivery vehicle.** Shortcuts Quick Action (lowest friction, recommended) vs. Hammerspoon
   (best hotkeys, if you already run it) vs. a menu-bar app (only if you want a UI).
4. **Language.** Python core is the recommendation (clipboard HTML reads + AST maturity). Confirm,
   or tell me Rust is a hard requirement and I will design around `clipboard-rs`.
5. **v1 scope.** Inline formatting + code blocks + lists + links only, or also tables and images
   from the start.

---

## 9. What I need from you

- **Copy any Slack message right now** (a fairly rich one: bold, a code block, a list, an
  @mention). Then tell me it is on the clipboard and I will inspect the actual pasteboard flavors
  and dump the HTML, so Phase 1 is built against your real Slack build, not an assumption.
- If we do the API paths (enrichment or posting), you would create a classic granular-scope
  Slack app on the `ibd` workspace and grab a bot token. I will give you the exact manifest and
  scopes when we get there.
