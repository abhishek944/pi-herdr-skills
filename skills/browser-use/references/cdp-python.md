# Python and raw CDP with the current Browser Use CLI

The current CLI executes Python from standard input. The old
`browser-use python "..."` command and command-mode helpers such as `state`,
`eval`, and `click` are removed.

Use a heredoc. Core helpers are pre-imported, and each invocation connects to
the selected daemon:

```bash
browser-use <<'PY'
ensure_real_tab()
print(page_info())
PY
```

Use one `BU_NAME` consistently when a task needs a named daemon:

```bash
BU_NAME=ui-check browser-use <<'PY'
print(current_tab())
print(list_tabs())
PY
```

## DOM and JavaScript

Use `js(...)` for focused DOM inspection or extraction:

```bash
browser-use <<'PY'
print(js("document.title"))
print(js("location.href"))
PY
```

After navigation, call `wait_for_load()` before reading the page.

## Accessibility tree and coordinate clicks

Prefer the accessibility tree when locating controls. Filter before printing
because a full tree can contain thousands of nodes.

```bash
browser-use <<'PY'
nodes = cdp("Accessibility.getFullAXTree")["nodes"]
for node in nodes:
    role = (node.get("role") or {}).get("value")
    name = (node.get("name") or {}).get("value")
    if role == "button" and name:
        print(name, node.get("backendDOMNodeId"))
PY
```

For a chosen node, obtain its viewport box and click the center:

```bash
browser-use <<'PY'
backend_id = 123  # replace with the selected backendDOMNodeId
quad = cdp("DOM.getBoxModel", backendNodeId=backend_id)["model"]["content"]
x = sum(quad[0::2]) / 4
y = sum(quad[1::2]) / 4
click_at_xy(x, y)
print(page_info())
PY
```

Negative or oversized coordinates mean the element needs scrolling first.
Coordinate clicks use CSS pixels.

## Screenshots

```bash
browser-use <<'PY'
capture_screenshot("/absolute/path/shot.png", max_dim=1800)
PY
```

Use `full=True` only when content below the fold is required. On high-DPI
screens, image pixels can differ from CSS click coordinates by
`window.devicePixelRatio`.

## Raw protocol calls

Use `cdp("Domain.method", **params)` only when normal helpers do not expose the
needed browser-level operation. Prefer documented helpers for tabs, input,
scrolling, screenshots, and recordings. Re-check the current Browser Use skill
and the matching interaction skill before inventing private API calls.
