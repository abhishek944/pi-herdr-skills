---
name: agent-review
description: "Repository-agnostic independent review for changes whose complexity, risk, breadth, uncertainty, or explicit user request justifies three readable review perspectives until clean. Straightforward confident implementations skip review; explicitly requested simple reviews use Sol and complicated reviews use Astra high. Requires Herdr-hosted Pi reviewers."
compatibility: Requires a Git repository, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry. Continue correcting and retrying while each failure is clearly non-mutating and provides actionable validation feedback; do not stop merely because an earlier correction revealed another issue. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, becomes ambiguous, or cannot be corrected from the documented interface. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Agent Review

Review the current change through three fresh, read-only Pi agents. Keep the reports useful to humans and repeat after fixes until the current code is clean.

## Recursive review guard

A reviewer launched by this workflow reviews directly. It must not edit files, run tests, or launch another agent.

## Rules

- Read repository instructions, the current diff, adjacent callers, relevant documentation, and existing checks.
- Resolve an explicit review mode, base, target, and scope.
- Review the live files immediately before launch; do not reuse an earlier verdict after code changes.
- Reviewers are read-only. The parent runs checks, verifies findings, and applies accepted fixes.
- Preserve unrelated user changes.
- Never commit, push, publish, or deploy merely to review.
- Keep only readable review reports; temporary launch diagnostics do not become implementation history.

## Review complexity

- **simple** — straightforward, low-risk work, including localized user-visible changes that follow an established pattern and are confidently covered by direct inspection plus normal checks;
- **complicated** — substantial features or work involving cross-boundary behavior, architecture, changed APIs or data contracts, authorization, security, privacy, destructive actions, migrations, concurrency, compatibility, resolved visual contracts, interacting failure modes, broad impact, or material uncertainty.

Implementation runs invoke review automatically only when their review gate classifies the work as feature or complicated. File count, diff size, and user-visible behavior alone do not require review. An explicit user review request always runs. Simple review uses Sol at high thinking. Complicated review uses Astra at high thinking.

## Existing decision contracts

Before reviewing, look for applicable Grill Me and UI/UX Grill Me decision trees under the current feature folder. If one exists, include its resolved decisions in each reviewer prompt. Deferred decisions are not requirements. If several applicable sessions exist and no selection is recorded, ask the user which one governs.

Do not create a separate contract pack. Reviewers inspect the selected decision tree and current implementation directly. Missing functionality or visual evidence is reported as a finding rather than encoded in a preflight artifact.

## Model routing

Follow the global `model-routing-policy` before every reviewer launch. Resolve `task_class: review`, the actual input types, review complexity, and contributor baselines. Pass provider, model, and thinking explicitly to Herdr.

Confirm the returned start response matches the requested provider, model, and thinking before prompting. This is an immediate launch check, not a durable review artifact. Do not add resolution, start-response, or launch-verification files to the implementation state.

Use three fresh reviewer instances. Reviewer recursion is disabled. A failed reviewer must be replaced only when the shared routing policy permits a confirmed no-contribution fallback.

## Herdr review wave

Follow the global `herdr` skill.

1. Create one dedicated unfocused review tab in the current workspace and repository. When review belongs to an `implement` run, immediately record that tab ID with `status: open` in `integration.review_resources`; this minimal cleanup record is required even if a later launch fails.
2. Use the root pane for correctness, split it right for architecture, and split the root down for regression. Never exceed four panes in a tab.
3. Give each pane a distinct descriptive name and apply the Herdr skill's bounded readiness check to every new pane.
4. Start all three Pi agents with explicit resolved provider, model, and thinking settings. Confirm each start response before sending prompts.
5. Prompt all three reviewers concurrently with a completion timeout of at least `900000` milliseconds (15 minutes).
6. Save only the final human-readable responses:

```text
var/<feature>/reviews/
  wave-<n>-correctness.md
  wave-<n>-architecture.md
  wave-<n>-regression.md
  wave-<n>-summary.md
```

7. Close every exact tab created by the wave after collecting the reports. Never close a pre-existing tab or workspace. For an `implement` run, change each recorded review resource to `status: closed` after absence is verified.

Temporary command output used while launching or diagnosing a reviewer belongs in the operating-system temporary directory and should not be retained as implementation evidence.

## Review perspectives

### Correctness and safety

Inspect behavior, data integrity, authorization, error handling, edge cases, destructive operations, and resolved product decisions.

### Architecture and integration

Inspect ownership boundaries, callers, API and configuration contracts, documentation accuracy, visual requirements, and maintainability.

### Regression and fix quality

Inspect realistic failure modes, compatibility, performance, operational impact, test gaps, and whether the fix addresses root causes.

Each report must include:

- review perspective and scope;
- actionable findings with severity and stable IDs, or none;
- concise evidence locations;
- exact footer lines:
  - `Reviewer instance: <immutable Pi session/instance ID>`
  - `Model: <provider/model-id>`
  - `Thinking: <level>`
  - `Finding IDs: <comma-separated IDs or none>`
  - `Verdict: <clean, pass, or blocked>`.

No additional machine markers are required.

## Triage and repeat

1. Read all three reports.
2. Combine duplicate findings by root cause in `wave-<n>-summary.md`.
3. Verify every finding against the current code and project rules.
4. Mark findings accepted, rejected, or unresolved with a short reason.
5. Apply authorized fixes and rerun affected checks.
6. If code changed after review, run a fresh complete wave and preserve the prior readable reports as history.
7. Stop when all three current-wave perspectives are clean or report the concrete blocker.

A reviewer timeout, missing output, blocked prompt, `agent_pane_busy` response, or unclosed owned tab prevents a clean verdict.

## Severity

- **P0:** immediate catastrophic risk or active security/data-loss issue.
- **P1:** likely serious correctness, security, or release blocker.
- **P2:** meaningful defect or regression that should be fixed before merge.
- **P3:** small but actionable issue with clear value.

Do not report style preferences without a practical impact or repository rule.

## Final report

Report:

- mode, base, target, and scope;
- selected decision-tree contracts or that none apply;
- three completed perspectives and their reviewer model settings;
- checks run by the parent;
- accepted, rejected, and unresolved findings;
- fixes applied and rechecked;
- review-tab cleanup;
- footer lines `Finding IDs: <comma-separated accepted/rejected IDs or none>` and `Verdict: <clean, pass, or blocked>`.
