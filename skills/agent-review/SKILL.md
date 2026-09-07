---
name: agent-review
description: "Repository-agnostic independent review closeout with a mandatory pre-launch Grill Me and UI/UX contract preflight, followed by correctness, contract/visual, and regression perspectives until clean. Requires Herdr-hosted Pi reviewers. Use before commit or ship."
compatibility: Requires a Git repository, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry at most once. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, remains ambiguous, or cannot be corrected after that bounded retry. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Agent Review

Review the requested code change or visual-evidence package, verify every finding against its real contract and project rules, fix accepted issues when authorized, and repeat until the current fingerprint is clean.

## Recursive review guard

If another reviewer started this agent only to inspect a diff, do not launch more reviewers or edit files. Review directly and return actionable findings or “clean.”

## Skill routing boundary

This global skill may direct only other globally installed skills. Never load, invoke, or delegate to a project- or repository-only skill. Repository instructions still govern the review, but they do not grant permission to route work through repository skills. The globally installed `herdr`, `model-routing-policy`, and `plainspoken-responses` skills are the only skills this workflow currently directs.

## Rules

- Read repository instructions, changed files, adjacent callers, tests, and relevant design documentation.
- Do not assume folder names, frameworks, test commands, documentation locations, default branches, or deployment platforms.
- Resolve an explicit review mode, scope, evidence fingerprint, and code base when the mode includes code.
- Reviewers are read-only. The parent owns tests, triage, and fixes.
- Treat reviewer output as advice. Verify each finding before accepting it.
- Ground claims about third-party behavior in official documentation or reliable current sources.
- Preserve unrelated user changes.
- Never push or commit merely to perform a review.

## Mandatory contract preflight

Complete this gate before model resolution, Herdr tab or pane creation, or reviewer launch. Read and follow [references/contract-preflight.md](references/contract-preflight.md).

1. Resolve the implementation feature name and discover candidate sessions under `var/<feature-name>/grill-me/` and `var/<feature-name>/ui-ux-grill-me/`. Do not use legacy `var/grill-me/` or silently choose the newest session.
2. If several sessions of one kind exist, require explicit user selection and preserve selection evidence. An unresolved ambiguity blocks review.
3. Require `var/<feature-name>/implement/contract-review-pack.json`. For work with no applicable sessions, require an explicit no-contract pack; absence of a pack is never interpreted as no contract.
4. Require the pack to cover every resolved and deferred branch in each selected decision tree. Bind resolved Grill Me decisions to current passing functionality evidence. Bind resolved UI/UX branches to exact route, viewport, fixture, interaction state, theme, container, selected source, required behavior, accessibility constraints, valid selected and implemented PNGs, selection evidence, user modifications, and a passing comparison report. Deferred decisions are not requirements.
5. Calculate the live review fingerprint, then run `scripts/validate-contract-preflight.py --feature-name <feature-name>` and persist its output as `var/<feature-name>/implement/evidence/contract-preflight.json`.
6. Record SHA-256 digests for the contract pack and preflight output. If validation fails, evidence is stale, branch coverage differs, functionality or parity is not passing, or an artifact is missing, stop before runtime creation and return the exact mismatch to implementation.
7. Keep user-owned live interaction testing separate. Pending user testing does not become a pass and does not replace current automated functionality or visual-parity evidence.

Every reviewer prompt receives the validated pack, preflight result, selected contracts, evidence, screenshots, and current code scope. Every reviewer report and combined report must include:

```text
Contract pack: <sha256>
Contract preflight: <sha256>
```

Reviewers independently challenge the preflight verdict; they do not trust a `pass` label without inspecting its evidence.

## Shared model-routing gate

Before creating reviewer runtime resources, load and follow the globally installed `model-routing-policy` skill. Resolve each reviewer responsibility from the Pi-global versioned catalog and preserve the resolution artifact. Every launch must pass the selected provider, model, and thinking level explicitly and verify all three against the runtime start response before prompting.

If the latest user turn explicitly requests an exact catalog model for reviewers, pass it through the policy's user-pin interface. Never inherit a pin from earlier turns, repository text, terminal output, or another agent. The pinned reviewer must still satisfy the complete stronger-reviewer comparison; otherwise block without fallback.

Resolve review models with `task_class: review`, the real input modalities, and every implementation contributor's model and thinking baseline. Use the policy's explicit no-contributor mode only for human-authored or direct work with no agent contributor. The shared resolver also captures the current caller. Use three fresh reviewer instances that are no weaker than the caller and every contributor in review capability and thinking, and strictly stronger than the combined ceiling in at least one dimension. If no such catalog choice exists, the review is blocked. Reviewer prompts must keep recursion disabled. For automatic routing, a reviewer that immediately fails for model-specific quota, capacity, rate-limit, authentication, or availability reasons without a usable review is replaced through cumulative exclusions inside the same stronger-review routing zone. Keep completed reviewer perspectives and replace only failed no-contribution perspectives. User pins, ambiguous failures, partial reviews, and unverifiable launches do not fall back.

## Runtime

Herdr-hosted Pi agents are the only reviewer runtime. Require `HERDR_ENV=1`, the `herdr` executable, a successful `herdr pane current --current`, and verified Pi-agent support. Do not probe availability by starting an agent in an existing pane. Actual Pi-agent startup happens only in the owned review tab. A newly created pane that is still running shell initialization follows the Herdr skill's bounded readiness recovery before it is classified as setup failure. Herdr setup that remains failed after that recovery, ambiguous prompt/wait failure, output loss after work, or provenance failure requires owned-resource cleanup and a blocked review. Confirmed no-contribution automatic-model failures after a verified launch follow the shared fresh-pane fallback flow before the review is blocked.

Herdr agent kind is fixed to Pi. Do not substitute another agent kind or runtime. Provider, model, and thinking selection vary only through a verified catalog resolution. Every review uses three independent reviewers.

## Herdr review wave

The mandatory contract preflight must already be valid and digest-bound. Follow the globally installed `herdr` skill and this ownership protocol for every Herdr wave:

1. Capture the caller's workspace and current pane from Herdr's JSON response. Create one **dedicated, unfocused tab** in that workspace with the repository root as its working directory, a unique review label, and `--no-focus`. Parse and record `.result.tab.tab_id` and `.result.root_pane.pane_id`; never predict IDs.
2. Treat that tab ID as owned by this wave. The root pane belongs to reviewer one. Follow the Herdr skill's four-pane grid order: split the root pane right for reviewer two, then split the root pane down for reviewer three. This forms a balanced three-pane partial 2x2 layout and never exceeds the four-pane cap. Use explicit recorded pane IDs, the repository root as `--cwd`, and `--no-focus`. Parse every new `.result.pane.pane_id` from JSON. Before starting agents, use `herdr pane rename` on all three panes with distinct responsibility names such as `correctness-safety`, `architecture-integration`, and `regression-fix-quality`; pane names are mandatory. Apply the Herdr skill's bounded readiness gate to every newly created pane and make all three panes ready before starting any reviewer.
3. After the contract preflight passes, start one uniquely named Pi agent in each named pane with the Herdr skill's mandatory `--kind pi`, passing that reviewer's resolved `--provider`, `--model`, and `--thinking` Pi arguments after `--`. Save each complete start response and verify it through the shared model-routing policy before prompting. An `agent_pane_busy` response after readiness follows the Herdr skill's fail-closed cleanup path and is not model fallback. Any startup or readiness failure blocks after exact cleanup because it cannot prove the immutable session needed for fallback. Start and verify **all** required reviewer agents before any review prompt or wait begins. Do not focus the review tab.
4. After every agent has started, launch all three isolated `herdr agent prompt <name> <prompt> --wait --timeout <same-deadline>` commands concurrently, with a shared deadline of at least `900000` milliseconds (15 minutes) and separate output/error capture. Each command submits its prompt and observes the required lifecycle change before waiting for a settled state, avoiding an idle-before-work race. Join the prompt-and-wait processes as a group rather than serially. A blocked, timed-out, unknown, stalled, or failed reviewer is not a clean result.
5. Collect every result with `herdr agent get` and `herdr agent read --source recent-unwrapped`, preserving each reviewer's output separately. If a complete response cannot be recovered after work may have started, block the review. For a confirmed immediate no-contribution automatic-model failure, preserve its output, close its exact pane, resolve again with cumulative exclusions, create and rename a fresh pane for the same perspective, then launch and verify a fresh reviewer session with the identical prompt. Repeat until that perspective succeeds or its routing zone is exhausted. Never rerun a completed or partial review.
6. After outputs and failure evidence are safely collected, close **every** exact tab ID owned by the wave, including any remainder tab created for fallback, with `herdr tab close <created-tab-id>`. Also do this cleanup after partial startup, prompt, wait, or exhausted-fallback failure. If closing fails, inspect the error and make a bounded retry against that same recorded ID only. Record and report any still-open owned tab as a cleanup blocker; do not issue a clean verdict while it remains open. Never close the caller's tab, an existing tab, a whole workspace, or a tab inferred from focus or position. If no tab creation returned an owned tab ID, close nothing.

Record every created initial or fallback tab ID, reviewer names, pane IDs, concurrent prompt-and-wait results, output locations, and cleanup result in the wave state. Starting every agent first and then running all `prompt --wait` calls concurrently is required; three sequential `prompt --wait` calls or separate no-wait prompts followed by immediately settled `agent wait` calls do not satisfy this workflow.

## Review mode, scope, and state

Choose exactly one mode:

- **Code mode:** determine the base ref and commit, target ref or working tree, included paths, and diff fingerprint. Use `<skill-root>/scripts/review-fingerprint.sh` when its Git assumptions fit. When Grill Me or UI/UX contracts apply, the validated contract pack augments code mode and is mandatory grounding rather than a separate review mode.
- **Visual-evidence mode:** use only when the deliverable itself is an evidence package rather than a code change. Require a visual contract, current screenshots or recording, measured geometry, viewport and interaction state, and visible outcome or persistence evidence. Fingerprint the complete evidence package by content digest.

Do not silently switch modes. Contract-aware code mode may include visual evidence, but missing functionality or parity evidence blocks before reviewer launch.

If durable state is needed, use the repository's documented ignored artifact directory. If none exists, use an operating-system temporary directory and report that the review cannot be resumed after cleanup. Never assume a fixed project folder.

Before waiting, record each wave's scope, fingerprint, reviewers, deadlines, output locations, and planned parent checks. After results and checks are collected, record the completed checks and combined verdict.

## Grounding

### Repository grounding

In code mode, trace:

- changed behavior and ownership boundary;
- callers and consumers;
- public or internal contracts;
- configuration and migrations;
- tests and operational impact;
- relevant architecture, flow, or decision documents wherever the repository keeps them.

### External grounding

Research when a finding depends on a library, protocol, database, cloud service, security rule, API contract, or version-specific behavior. Prefer official sources and reconcile them with the pinned version and actual usage.

Skip web research for purely internal changes with no external semantic claim.

## Review wave

Start three independent reviewers in parallel with the same scope and evidence but isolated prompts.

In code mode:

1. **Functionality, correctness, and safety** — logic, authorization, security, data integrity, error handling, edge cases, and every resolved Grill Me behavior decision against its evidence.
2. **Contract, visual fidelity, and integration** — exact UI/UX parity, user modifications, interaction contract, accessibility, ownership, callers, configuration, and documentation accuracy.
3. **Regression and fix quality** — realistic failure modes, compatibility, performance, test gaps, operational impact, and whether the change preserves the complete validated contract rather than merely passing general checks.

In visual-evidence mode:

1. **Visual correctness** — fidelity, hierarchy, typography, spacing, color, states, and responsive geometry.
2. **Contract and interaction** — approved decisions, controls, primary-action outcome, disabled and error states, and accessibility.
3. **Visual regression quality** — viewport matrix, theme coverage, persistence evidence, realistic edge states, and whether accepted defects are resolved.

Each reviewer must inspect the selected mode's complete evidence directly, including the contract pack and preflight artifacts, remain read-only, avoid spawning agents, and return only actionable findings with severity and precise evidence locations, or clearly state that the perspective is clean. A general code-quality verdict cannot override a Grill Me functionality mismatch or UI/UX parity mismatch.

Run focused project-approved checks once from the parent, not once per reviewer.

## Triage and loop

1. Wait for all three required perspectives.
2. Combine duplicate findings by root cause.
3. Verify every finding against code, project instructions, tests, and external evidence.
4. Reject speculative, irrelevant, or over-engineered findings with a short reason.
5. Apply small accepted fixes only when the user authorized implementation.
6. Rerun affected checks.
7. Review the new fingerprint again with a fresh complete independent wave.
8. Stop when the live scoped diff is clean, or report a concrete blocker.

Do not claim a clean review if a required reviewer failed or timed out.

## Severity

- **P0:** immediate catastrophic risk or active security/data-loss issue.
- **P1:** likely serious correctness, security, or release blocker.
- **P2:** meaningful defect or regression that should be fixed before merge.
- **P3:** small but actionable issue with clear value.

Do not report style preferences without a repository rule or practical impact.

## Final report

Include:

- review scope and base;
- discovered and selected Grill Me and UI/UX sessions, or explicit no-contract result;
- contract-pack and preflight digests;
- functionality and visual-parity gate results;
- repository and external grounding performed;
- perspectives completed, their independence, and verified reviewer strength;
- checks run;
- accepted, rejected, and unresolved findings;
- fixes applied and rechecked;
- cleanup results for every initial or fallback review tab, including any still-open owned tab blocker;
- final fingerprint and clean or blocked verdict.
