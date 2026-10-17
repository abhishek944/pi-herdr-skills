# Visibility, clipping and occlusion protocol

Run this in the actual integrated layout. A perfectly rendered component can still be hidden by its parent or sibling.

## Observe before correcting

1. Capture the viewport before interaction, then click the real trigger and capture the initial open state. Do not force-click or scroll the panel into view first.
2. Identify the actual surface, its anchor and meaningful content/actions. Inspect DOM plus the screenshot; mounting and computed `display` do not establish that a user can see it.
3. Record its rectangle, viewport/visualViewport and relevant pane rectangle. At mobile zoom, visual viewport offsets and dimensions can differ from layout viewport values.
4. Inspect the ancestor chain for `overflow: hidden/clip/auto/scroll`, `contain`, transforms, stacking contexts, positioning and z-index. Check siblings such as a composer or sticky footer, not just ancestors.
5. Separate clipping (paint cut off by a boundary), occlusion (another layer painted above), offscreen placement and intentional scrollable overflow. Multiple causes can coexist.

## Useful browser diagnostic

Adapt the selector to the actual surface; run through the available browser's page-evaluation facility. This is an investigative snippet, not a unit test or a universal pass/fail detector.

```javascript
(() => {
  const el = document.querySelector('REPLACE_WITH_SURFACE_SELECTOR');
  if (!el) return { found: false };
  const r = el.getBoundingClientRect();
  const v = window.visualViewport;
  const viewport = {
    x: v?.offsetLeft ?? 0, y: v?.offsetTop ?? 0,
    width: v?.width ?? innerWidth, height: v?.height ?? innerHeight,
  };
  const label = node => node ? {
    tag: node.tagName, id: node.id,
    role: node.getAttribute('role'), cx: node.getAttribute('data-cx'),
  } : null;
  const points = [[.5, .15], [.5, .5], [.5, .85], [.1, .5], [.9, .5]];
  const samples = points.map(([x, y]) => {
    const px = r.left + r.width * x, py = r.top + r.height * y;
    const hit = document.elementFromPoint(px, py);
    return { x: px, y: py, insideSurface: hit !== null && el.contains(hit),
      topElement: label(hit) };
  });
  const ancestors = [];
  for (let node = el; node; node = node.parentElement) {
    const s = getComputedStyle(node);
    ancestors.push({ ...label(node), overflowX: s.overflowX,
      overflowY: s.overflowY, position: s.position, zIndex: s.zIndex,
      transform: s.transform, contain: s.contain,
      rect: node.getBoundingClientRect().toJSON() });
  }
  return { found: true, rect: r.toJSON(), viewport, samples, ancestors,
    scroll: { clientHeight: el.clientHeight, scrollHeight: el.scrollHeight,
      clientWidth: el.clientWidth, scrollWidth: el.scrollWidth } };
})();
```

Hit-testing is supporting evidence only. Pointer-events, transparent overlays, borders, rounded corners and intentional scrolling can make samples misleading. Do not change CSS to manufacture a pass. A pointer-events:none element can still visually cover content without appearing as the top hit target. Inspect screenshots in every case.

Repeat measurements for meaningful descendants, especially the last value/action, rather than relying on the panel's center. For an actionable descendant, inspect its own rectangle and an interior hit point; descendants of that control are valid hits. Use a normal click and verify the actual expected outcome only when the action is safe and authorized.

## Reachability and lifecycle

- Preserve the initial failure, then attempt normal wheel/touchpad/keyboard scrolling in the intended container. Record which container moves and whether the last content/action becomes usable.
- Offscreen content is not automatically a defect if the intended scrolling can reveal it without losing essential controls. Document-level sideways scrolling or unreachable final actions are not an acceptable substitute for a bounded popover.
- Inspect the accessibility tree and Tab order. DOM presence, accessible names or programmatic focus do not prove a control is visually exposed or pointer-operable.
- Resize the pane and viewport while open, including reduced height. Check fixed/sticky siblings and bottom/right edges; overlays must fit, intentionally scroll, reposition or dismiss coherently.
- Test Escape, outside click where applicable, reopen and trigger focus return. Do not treat a non-modal panel's lack of a focus trap as a bug.
- For touch/mobile layouts, record whether an actual software keyboard was exercised; a desktop viewport emulation does not prove keyboard avoidance.

## Evidence-backed failure

For each defect retain: natural screenshot, control and route, exact viewport/pane/zoom/theme, initial scroll, steps, affected content/action and measured clipping/occluding element. Avoid personal text in exported DOM labels. A panel behind a composer is a failure even when its bounding box is fully inside the viewport.

Do not claim a root cause from one computed property. If source and paint-order evidence are unavailable, report the observed failure and a labeled hypothesis. Recheck identical conditions after an authorized fix; a new isolated fixture is not a substitute for the original integrated scenario.
