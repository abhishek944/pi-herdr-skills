---
name: ui-ux-testing
description: "Test an existing UI through real browser interactions to find clipped or covered popovers, inaccessible controls, overflow, responsive-layout problems, confusing focus states and broken interaction flows. Use for UI/UX audits, visual regression checks, or screenshots showing layout defects. Reports evidence and coverage; does not redesign or fix the app unless requested."
compatibility: Requires an accessible application and an authorized browser or desktop automation tool for runtime verification.
---

# UI/UX Testing

Find what breaks when someone actually uses the interface, not just when it first renders.
Before replying, follow `talk-human`. Follow `no-unit-tests`; UI testing does not authorize unit tests.

## Scope and safety

- Read repository instructions, relevant flow docs, design contracts and the reported screenshot first.
- Identify the target URL/build, affected workflow, supported devices/themes and allowed actions.
- A request to run this skill authorizes non-mutating UI inspection, navigation, opening overlays and temporary search input. Check for autosave before typing into other fields.
- Do not submit forms, send messages, make paid calls, enable microphone/camera, upload files, delete data or change persistent settings without authorization.
- Do not bypass authentication. Stop for passwords, MFA, permission prompts or unclear account choice. Do not extract cookies or credentials.
- Do not install browsers/dependencies, restart services, rebuild live assets or deploy without the required authority. Preserve unrelated work and user-owned resources.
- Default to testing and reporting only. Implement fixes only when the user also requests them; then use `implement` and recheck the original failure.

## Coordination and tools

Use existing Work/Todo records and keep them current when available. Never change tracking during `/ask` or `/btw`. Use monitors for background commands; do not create polling loops for an ordinary audit.

Read `browser-use` for browser operation. Prefer an isolated local browser with already-installed tools; an installed Playwright runtime is acceptable when the browser harness cannot connect. Do not silently switch to a paid remote browser. For native apps, read `computer-use` and use its verified screenshot/accessibility workflow.

Close only owned browsers/contexts in `finally`. Never close a personal tab or another worker's service. Keep waits bounded; after a failed wait inspect the page before one additional bounded attempt.

Keep reports under `var/<feature-name>/ui-ux-testing-details/`. Browser-tool screenshots stay under `var/<feature-name>/browser-use-details/`; link them from the report. Protect private data in captures and do not retain raw sessions in memory.

## 1. Establish the real baseline

1. Reproduce the reported path with actual controls in the current application. Capture the initial full viewport, then the opened/failing state.
2. Record URL/route, source/build identity when available, browser/version, viewport in CSS pixels, device scale factor, zoom, theme, pane sizes, scroll position and relevant data state. Do not dump environment values.
3. Use the actual page layout: the real ancestors, footer/composer, sidebar, sibling overlays, fonts, scroll containers and stacking contexts matter.
4. If access is blocked, report **BLOCKED**. A screenshot-only diagnosis is a hypothesis. An anonymous fixture may supplement investigation but cannot pass a live integration gate.
5. Do not inject CSS, force-click, hide surrounding components or scroll a target into view before capturing the natural failure. Browser automation may auto-scroll; record when it does.

## 2. Write a bounded coverage matrix

List each distinct trigger/state before running checks. Do not count two buttons as covered because they look alike; Context and Cost can open different panels.

| Axis | Minimum relevant coverage |
| --- | --- |
| Interaction | Closed, opened by pointer, opened by keyboard, dismissed, reopened; each distinct trigger |
| Layout | Current layout, narrowest supported pane, smallest supported viewport, short-height desktop |
| Viewport | Actual user size; if unspecified, add 1280×800, 1280×600 and 360×800 CSS pixels, labeling assumptions |
| Scroll | Top and bottom; middle when sticky/fixed elements or long content can affect placement |
| Content | Empty/short and realistically long labels/details; loading/error/disabled states when safely available |
| Accessibility | Tab/Shift+Tab, activation, Escape, focus return, 200% browser zoom or equivalent reflow check |
| Theme | Current and supported light/dark alternatives; inspect other supported palettes for contrast/state regressions |

Prioritize reported failures and shared overlays, then adjacent controls. State omissions explicitly; do not invent every possible state or run an unbounded Cartesian product. Device scale factor is not browser zoom; label emulations and unavailable mobile-keyboard checks honestly.

## 3. Check every opened surface in context

Read [the visibility protocol](references/visibility.md) before checking clipping, overflow or layered surfaces.

For popovers, menus, tooltips, dialogs, dropdowns, inspectors and expanded panels:

- Inspect the whole surface in a full-viewport screenshot, not only a cropped heading or its DOM presence.
- Check top/bottom/left/right edges against the visual viewport and intended pane. No text, action or close control may be silently cut off.
- Inspect overflow ancestors and stacking contexts. A high child z-index cannot escape a lower ancestor layer. Look for composers, sticky footers and sibling panels covering content.
- Verify title, representative middle content, final row/value, close control and primary actions are visible or genuinely reachable by the intended scrolling.
- Check pointer hit targets and keyboard reachability. A passing bounding rectangle, `isVisible()`, screenshot hash or successful force-click is not proof of visibility.
- Open near each relevant edge. Resize the viewport/pane and scroll the parent while open; confirm the overlay repositions, scrolls appropriately or deliberately dismisses.
- For long content, verify an intentional scroll container and that its final item can be reached. Scrolling the background must not masquerade as scrolling a modal.
- Check anchor relationship, overlap between simultaneous overlays, outside-click/Escape behavior and focus return. Modal focus stays inside; non-modal panels need not trap focus.

**Required regression example:** open Context and Cost separately above a chat composer at short height and a narrow pane. Verify the middle and bottom of each details panel are not behind the composer, even when the entire panel rectangle lies inside the viewport.

## 4. Check everyday usability

- Search: click, type, clear, no-results, Escape and keyboard navigation; inspect unexpected rings, underlines, jumps or text clipping.
- Forms: labels, caret/focus discoverability, error text, disabled/busy distinction and stable geometry; do not submit without authorization.
- Navigation: active state, Back/Forward, reachable actions and no accidental document-level horizontal scrolling.
- Dense layouts: long names, wrapped text, scroll areas, fixed headers/footers, menus near viewport edges and controls at 200% zoom.
- Keyboard: logical order, visible focus consistent with approved styling, no focus hidden beneath overlays, correct Escape target and restored trigger focus.
- Feedback: loading/error/empty states are distinguishable; do not trigger billable or destructive work merely to generate a state.
- Record browser errors and relevant failed requests without copying tokens, private payloads or full logs. Automated accessibility findings supplement, not replace, visual inspection.

Do not replace a user-rejected decoration with another invented one. Preserve approved interaction and visual decisions unless explicitly changed.

## 5. Report evidence, not confidence theatre

Create `report.md` with:

1. **Scope/environment:** target build and exact tested layouts/states; live page versus fixture evidence.
2. **Findings:** severity, affected control/route, reproducible steps, expected versus observed behavior, screenshot path and supporting measurements.
3. **Cause:** confirmed owning selector/component when source evidence establishes it; otherwise label the cause a hypothesis. Suggest the smallest correction without applying it by default.
4. **Coverage:** one row per actual case with PASS/FAIL/BLOCKED/NOT RUN and linked evidence. A reproducible defect is FAIL, not BLOCKED. No silent skips or blanket "all UI passed" claims.
5. **Limits/next action:** unavailable auth/device/data/browser states, risky steps not attempted, and the exact scenarios that a fix must recheck.

Severity follows user impact: blocked essential action or serious access failure is high; obscured recoverable content is medium; purely cosmetic issues are low. Explain the impact rather than guessing a priority from appearance alone.

Each finding needs its natural failing state. Screenshots plus reproduction steps are required; DOM measurements alone are insufficient. Include a wider context capture when a crop hides the occluding layer. Redact sensitive content without hiding the defect.

After an authorized fix, rerun the same failing state and adjacent edge/keyboard cases, capture the corrected state, and check for new regressions. Do not call an issue fixed solely because CSS changed or lint/build passed.

Finish with the important findings, report path and blockers. If no defects were found, say **no issues found in the tested scope**, not that the product is certified accessible or universally regression-free.
