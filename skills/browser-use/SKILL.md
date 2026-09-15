---
name: browser-use
description: Automates browser interactions for web testing, form filling, screenshots, and data extraction.
allowed-tools: Bash(browser-use:*) Bash(grep:*)
compatibility: Requires the browser-use CLI and its browser-harness runtime.
---

# Browser Use

Use Browser Use when a task needs a real browser: JavaScript rendering, clicks, forms, screenshots, downloads, or an existing signed-in session. Use normal web fetching for public pages that do not need interaction.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read repository instructions before starting an app or choosing a port.
- Do not close tabs, browsers, or services you did not create.
- Stop for personal passwords, multi-factor authentication, consent, or an unclear account choice.
- Keep waits bounded to 120 seconds. Inspect the page before trying one additional bounded wait.
- Prefer accessible names and the accessibility tree for finding controls.
- Verify every click, navigation, and form value after performing it.
- Never expose credentials or private data in output or screenshots.

## Basic use

Browser actions run as Python through standard input:

```bash
browser-use <<'PY'
new_tab("https://example.com")
wait_for_load()
print(page_info())
PY
```

Reuse the same task tab with `current_tab()`, `list_tabs()`, and `switch_tab()`. Common helpers include `click_at_xy`, `fill_input`, `press_key`, `js`, `wait_for_element`, and `capture_screenshot`.

If local Chrome cannot connect, run `browser-use --doctor`. Use a named remote browser only when isolation or a hosted browser is genuinely needed, and ask before leaving a paid remote browser running.

## Files

If the task needs screenshots, downloads, or notes, write them only under:

```text
var/<feature-name>/browser-use-details/
```

## Final response

Report what was done, what was observed, saved files, and any user action still required.
