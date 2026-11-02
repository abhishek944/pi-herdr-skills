---
name: ui-ux-testing
description: "Audit UI/UX with dedicated parallel subagents for workflows, overlays, responsive layout, accessibility, forms/search/navigation, themes and cross-screen component reuse. Use for UI/UX audits, visual regression checks, or screenshots showing defects or inconsistent controls. Automatically implement validated in-scope fixes using shared components and recheck them; stop at a report only when explicitly asked for audit-only/read-only work."
compatibility: Requires Herdr Core and dedicated visible Herdr app tabs for delegated Pi auditors, an accessible application, and authorized browser or desktop automation for runtime verification.
---

# UI/UX Testing

Find what breaks when someone actually uses the interface, then fix validated in-scope defects and verify the result—not just the first render.
Before replying, follow `talk-human`. Follow `no-unit-tests`; UI testing does not authorize unit tests.

## Scope and safety

- Read repository instructions, relevant flow docs, design contracts and the reported screenshot first.
- Identify the target URL/build, affected workflow, supported devices/themes and allowed actions.
- A request to run this skill authorizes non-mutating UI inspection, navigation, opening overlays and temporary search input. Check for autosave before typing into other fields.
- Do not submit forms, send messages, make paid calls, enable microphone/camera, upload files, delete data or change persistent settings without authorization.
- Do not bypass authentication. Stop for passwords, MFA, permission prompts or unclear account choice. Do not extract cookies or credentials.
- Do not install browsers/dependencies, restart services, rebuild live assets or deploy without the required authority. Preserve unrelated work and user-owned resources.
- Normal invocation includes automatic implementation of validated in-scope local source fixes and permitted verification. Do not stop at the findings report or ask a redundant "should I fix these?" question. An explicit audit-only, read-only or no-changes request overrides this default; consequential actions still need their own authority.

## Coordination and tools

Use existing Work/Todo records and keep them current when available. Never change tracking during `/ask` or `/btw`. Use monitors for background commands; do not create polling loops for an ordinary audit.

Read `browser-use` for browser operation. Prefer an isolated local browser with already-installed tools; an installed Playwright runtime is acceptable when the browser harness cannot connect. Do not silently switch to a paid remote browser. For native apps, read `computer-use` and use its verified screenshot/accessibility workflow.

Close only owned browsers/contexts in `finally`. Never close a personal tab or another worker's service. Keep waits bounded; after a failed wait inspect the page before one additional bounded attempt.

Follow global `implement` for canonical task ownership. Keep aggregate reports inside the parent's task directory and each worker's report/screenshots inside its own canonical task directory, nested below the exact supplied parent task directory using that worker's real session/Work/Task IDs. Reuse caller tracking for the same assignment; standalone work establishes its own tracked owner first. Link exact original evidence paths from the aggregate report; never reconstruct feature or lane folders. Protect private data in captures and do not retain raw sessions in memory.

## Validate the testing method before expanding coverage

- Follow `browser-use`'s simple testing loop: start with direct actions or short inline batches, prove each step, then automate only stable repeated sequences. Do not create a long custom harness before reproducing one real case.
- Establish a positive control within existing authorization before declaring input or observation broken. Confirm the actual page/frame and visible value/result; validate any custom observer before treating its silence as product evidence. Do not change application state, caret or model internals merely to satisfy a test.
- Keep related steps in one owned browser/page within supported lifetimes. Avoid unnecessary account/profile recreation or one launcher invocation per screenshot; retain useful failure context until collected, then clean up only owned resources.
- After two failures at the same step, stop cycling through variants. Inspect whether the tool, test assumptions or application failed, and choose one evidence-backed next step. No new evidence means report the limitation, not another blind retry or a generic permission question.
- For persistence cases, distinguish value entry, application acknowledgement, completed server save/drain and fresh reopen. Check each boundary rather than inferring the full workflow from an intermediate success.
- Separate application defects from test/tool failures in the coverage report. Mark a check **TOOLING FAILURE; application NOT VERIFIED** when its observer, selector or harness is faulty; preserve its original evidence and do not present it as an application defect or a pass. A genuine reproduced application defect remains FAIL.
- Complete this preflight before fan-out. Give auditors the validated interaction method and known tool limits so they do not independently repeat the same failed setup.

## Parallel auditors: maximize useful coverage

Assign a different dedicated subagent to each applicable area below; do not bundle unrelated areas into one generalist audit. Run independent areas concurrently to speed up coverage within actual browser/tool capacity and explicit user budgets. If capacity is limited, schedule distinct area owners in waves rather than silently merging responsibilities. Record owners, dependencies, constraints and any area omitted as not applicable or blocked. Expand a busy area across disjoint routes when useful; do not duplicate cases or invent irrelevant work.

Complete baseline/access preflight and the coverage matrix before dispatch. Avoid spawning agents just to rediscover a known authentication or tooling blocker. While runtime access is blocked, independent source inspection and coverage review may proceed, but cannot count as live UI passes.

Select global herdr for Core-hosted Pi agents and read it before launching. Verify the real HC_TERMINAL_ID parent and app space; do not require HERDR_ENV or the old TUI CLI. Read model-routing-policy and apply its UI/UX-testing session route and higher-priority exceptions. Verify image support for screenshot reviewers. If Core, the app, required models or continuous monitoring are unavailable, report the precise tooling blocker; do not silently substitute a single-agent audit.

### Critical workflows agent

Assign a dedicated workflow auditor for primary actions, button versus keyboard submission, disabled/busy explanations and safe failure recovery. Observe sending, paid or destructive workflows only within explicit authorization.

### Overlay visibility agent

Assign a different overlay auditor for dropdowns, popovers, dialogs, tooltips and inspectors. Check clipping, occlusion, edge placement, scroll reachability, dismissal and reopen in the integrated layout.

### Responsive layout agent

Assign a different layout auditor for narrow panes/screens, short windows, resizing, zoom/reflow, overflow and sticky/fixed siblings. Check both viewport bounds and actual pane bounds.

### Keyboard and accessibility agent

Assign a different accessibility auditor for Tab/Shift+Tab order, activation, visible focus, focus return, Escape, labels, semantic roles and modal containment. Do not claim accessibility certification from automated checks.

### Forms, search and navigation agent

Assign a different interaction auditor for typing, clear controls, no-results, validation, loading/error states, Back/Forward and active navigation. Compare search behavior across relevant routes without unauthorized submissions or autosaves.

### Themes and content agent

Assign a different visual-content auditor for supported palettes, contrast, density, typography, long labels, wrapping and empty/loading/error states. Compare against approved visual contracts, not an invented redesign.

### Component reuse and visual consistency agent

Always assign a dedicated consistency auditor for changed UI controls. Inventory existing shared components and equivalent uses across screens, including components outside `components/ui/`. Compare Files versus Settings dropdowns and Files versus Chats search fields when present, plus buttons, tabs, notices and menus. Flag raw controls, copied markup, divergent icons, spacing, borders, typography and interaction states that bypass the shared component without a documented requirement. Record each location, canonical component, evidence and smallest reuse fix; distinguish justified variants. Require validated fixes to reuse the common component, not copy its CSS or create another lookalike. Hand shared-file changes to the implementation owner; verify consistency at every affected use afterward.

### Source investigation agent

Assign a different read-only source investigator to trace observed symptoms to owning components, CSS and callers. Check lifecycle and dependency boundaries; label hypotheses and source-only findings separately from reproduced browser failures.

### Independent findings review agent

Assign a different synthesis reviewer once area reports are ready. Reconcile duplicate causes, challenge unsupported passes/findings, check missing coverage and scope, and ensure component-reuse findings have explicit dispositions. This reviewer does not substitute for the original area audits.

### Implementation agents

After findings are validated, assign separate implementation subagents with disjoint file ownership and acceptance criteria. Give shared-component reuse/refactors to one owner, including its affected callers; dependent fixes wait for that shared change. Do not have audit workers edit source during evidence collection or let multiple agents modify the same component concurrently. Reuse existing components and preserve behavior, accessibility and approved variants; extract a minimal common component only for proven duplication when none fits.

### Regression verification agent

Assign a different verification subagent from the fix author after the relevant changes are integrated. Repeat original failing cases and adjacent keyboard, responsive and theme states; recheck all consumers of changed shared components. Keep unavailable live checks blocked rather than replacing them with fixture/static passes. The parent still owns final integration and verification.

Keep area owners distinct for the audit pass. Run ready independent work in parallel; order synthesis, shared-state checks, implementation dependencies and regression instead of racing them.

### Dispatch and isolation contract

1. The parent creates one Todo per lane and a final integration Todo under the audit Work, and owns the aggregate matrix with unique case IDs. Give each worker its case IDs, target build/routes, viewports/states, allowed/prohibited actions, browser ownership and report paths. Audit workers do not edit the parent's aggregate report or application source; phase 6 assigns separate implementation owners.
2. Follow herdr: one dedicated visible task-named app tab per worker, explicit verified model settings, actual terminalId/tabId handles, and a continuous MonitorCreate with hcTerminalId, timeout:0 and onSignal. Confirm native Pi input readiness and MonitorList's Core subscription ready receipt before prompting. No hidden-worker substitute, one-shot waits or unmonitored dispatch.
3. Give each browser auditor an exclusive page and preferably a separate browser context. Tabs alone do not isolate storage/theme synchronization or shared account/server state. Allocate authorized isolated test state, or serialize conflicting actions. Do not extract cookies or clone credentials to manufacture isolation.
4. Never have multiple agents drive the same page, focused desktop or user browser simultaneously. A shared native desktop gets one UI owner at a time; other agents may inspect source/evidence in parallel. Report the live-coverage limit rather than pretending parallel screenshots exercised separate sessions.
5. Each worker writes `<workerTaskDir>/report.md` and `<workerTaskDir>/screenshots/` inside its own canonical nested task directory from global `implement`. Pass the exact parent task directory; require the worker's real local session/Work/Task IDs and returned artifact root. Lane names are metadata, not directory ownership keys. Require exact case results, reproduction steps, screenshots, environment, blockers and action limits. Workers inherit all safety gates; delegation grants no additional permission. No recursive subagents unless the parent explicitly authorizes them.
6. Keep each owned monitor across working/blocked/idle/done and follow-up states. Inspect real worker status and the complete result, not status signals alone. Resolve blockers or reassign safe cases; do not recreate subscriptions for stale signals or monitor unrelated sibling parents.
7. The parent reads every complete worker report, opens finding screenshots, reconciles unique case IDs and deduplicates findings without hiding different triggers. Reproduce material defects when authorized; otherwise label them worker-reproduced or not independently reproduced. Source-only and fixture checks remain separate from live results. A worker's done signal is not an acceptance gate.
8. Run the synthesis lane once evidence is ready, resolve conflicting findings and publish the audit baseline with per-lane coverage. Unless explicitly audit-only, continue immediately to phase 6; the report is a handoff artifact, not the end of the task. Retire or retask completed roles according to model-routing policy. Close only owned monitors/tabs/contexts after their verified work and required follow-ups, preserving resources still needed for implementation or rechecks.

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
- Chat keyboard contracts: where specified, Enter sends, Shift+Enter inserts a newline, and IME composition does not submit. Compare Enter with the Send button and inspect disabled reasons; actual sends still require authorization, including paid-model permission.
- Navigation: active state, Back/Forward, reachable actions and no accidental document-level horizontal scrolling.
- Dense layouts: long names, wrapped text, scroll areas, fixed headers/footers, menus near viewport edges and controls at 200% zoom.
- Keyboard: logical order, visible focus consistent with approved styling, no focus hidden beneath overlays, correct Escape target and restored trigger focus.
- Feedback: loading/error/empty states are distinguishable; do not trigger billable or destructive work merely to generate a state.
- Record browser errors and relevant failed requests without copying tokens, private payloads or full logs. Automated accessibility findings supplement, not replace, visual inspection.

Do not replace a user-rejected decoration with another invented one. Preserve approved interaction and visual decisions unless explicitly changed.

## 5. Report evidence, not confidence theatre

Create `report.md` with:

1. **Scope/environment:** target build and exact tested layouts/states; live page versus fixture evidence; worker/lane allocation and concurrency limits.
2. **Findings:** severity, affected control/route, reproducible steps, expected versus observed behavior, screenshot path and supporting measurements.
3. **Cause:** confirmed owning selector/component when source evidence establishes it; otherwise label the cause a hypothesis. Record the smallest scoped correction for phase 6; do not treat an unconfirmed cause as an implementation requirement.
4. **Coverage:** one row per actual case with PASS/FAIL/BLOCKED/NOT RUN and linked evidence. A reproducible defect is FAIL, not BLOCKED. No silent skips or blanket "all UI passed" claims.
5. **Remediation/limits:** each finding's implementation owner/status, verification results, unavailable auth/device/data/browser states, risky steps not attempted and exact rechecks. Keep the original failing evidence intact.

Severity follows user impact: blocked essential action or serious access failure is high; obscured recoverable content is medium; purely cosmetic issues are low. Explain the impact rather than guessing a priority from appearance alone.

Each finding needs its natural failing state. Screenshots plus reproduction steps are required; DOM measurements alone are insufficient. Include a wider context capture when a crop hides the occluding layer. Redact sensitive content without hiding the defect.

## 6. Automatically implement and recheck

Normal execution is **audit → validate/triage → implement → regression check**, not audit → ask whether to implement. An explicit audit-only/read-only request ends after the reviewed report; otherwise continue within the same work without waiting for another user message. This applies to running the audit, not a request merely to explain or edit this skill.

1. Revalidate findings against current source and approved behavior. Maintain a ledger linking finding IDs, evidence, accepted cause, owned files, fix Todos and required regression cases. Implement confirmed actionable in-scope defects, including source-confirmed defects when live access is unavailable. Do not patch an unproven hypothesis or invent a redesign to fill coverage gaps.
2. Read and follow `implement`; use its written plan, Todo/DAG, ownership, integration and review workflow. Follow `codebase-design` when that workflow requires it. Preserve unrelated edits and original screenshots/reports; scope fixes to the responsible boundary.
3. Maximize useful parallel implementation with disjoint file owners and dependencies, not simultaneous edits to shared code. Follow `model-routing-policy`'s UI/UX-testing session route and the mandatory Herdr monitoring contract. Keep evidence-collecting auditors read-only; assign implementation and independent regression owners as specified above. Route validated consistency findings to common-component reuse fixes, covering every affected caller without widening scope.
4. Do not let an unrelated auth, paid-call or device blocker stop safe independent source fixes. Ask only when an action truly needs credentials/consent, additional authority, a consequential product decision or an unsafe/out-of-scope change. Never bypass a gate or expand existing permissions to manufacture a pass.
5. Run the repository's required non-unit formatting/lint/type/build checks and proportionate review. Respect service-stop-before-build, watcher-free/manual restart and deployment constraints. Unit tests still require explicit permission in the latest user request. Ordinary source fixing does not authorize account/data writes, model charges, new installs, commits or deployments.
6. Rerun each original failing state and adjacent edge/keyboard cases within available permissions; capture the corrected state and inspect for new regressions. Source checks or fixtures supplement, never impersonate, blocked live integration. If a required live check is inaccessible, record **implemented; live verification BLOCKED**, not universally fixed.
7. Resolve in-scope regressions and repeat the affected checks until accepted fixes pass or a genuine blocker remains. Do not ask for continuation after every finding or stop merely because the audit report is written. Never treat an attachment-only Enter correction as proof that an unresolved text-only Enter complaint is fixed.
8. Update the report with **fixed and verified**, **implemented but verification blocked**, **unresolved**, **rejected**, or **blocked before implementation**, with evidence and reasons. Close completed owned resources and give a final handoff only after all runnable implementation/verification work is done; report the exact remaining authority/access dependency.

If no actionable defects were found, report **no issues found in the tested scope** and do not invent changes. Otherwise finish with what changed, actual checks/rechecks, remaining findings/blockers, evidence paths and owned-resource cleanup—not just a list of proposed fixes. Do not claim accessibility certification or a fix solely because CSS changed or lint/build passed.
