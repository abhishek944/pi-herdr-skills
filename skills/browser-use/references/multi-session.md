# Multiple Browser Use daemons

The current Browser Use CLI no longer accepts `--session` or `BROWSER_USE_SESSION`.
Use `BU_NAME` to route every invocation to one named harness daemon.

## One name per task or worktree

Choose a short, descriptive name and export it before the first browser call:

```bash
export BU_NAME=bloom-ui-4100
browser-use <<'PY'
new_tab("http://localhost:4100")
wait_for_load()
print(page_info())
PY
```

Every later `browser-use` invocation in that shell uses the same daemon. For an
isolated one-off call, prefix the command instead:

```bash
BU_NAME=docs-preview browser-use <<'PY'
new_tab("file:///absolute/path/to/preview.html")
print(page_info())
PY
```

A named local daemon is isolated at the harness state level, but it can still
attach to the same running Chrome as another daemon. Keep one working tab per
task, inspect `current_tab()` and `list_tabs()`, reuse it with `switch_tab()`, and
never close tabs you did not create.

## Remote isolation

Use one Browser Use Cloud daemon per truly parallel task:

```bash
browser-use <<'PY'
print(start_remote_daemon("scraper-a"))
PY

BU_NAME=scraper-a browser-use <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

Keep the same `BU_NAME` for all work on that remote browser. Remote daemons may
continue billing until stopped. Ask the user before stopping a still-running
remote browser, then use:

```bash
browser-use <<'PY'
stop_remote_daemon("scraper-a")
PY
```

## Cleanup

There is no current `browser-use close`, `close --all`, or `sessions` command.
Close only tabs created by the task with the documented tab helpers. Use
`stop_remote_daemon(name)` for a Browser Use Cloud daemon. Use
`browser-use --reload` only when intentionally restarting the local harness
daemon, such as after a CLI code update; it is not normal per-task cleanup.
