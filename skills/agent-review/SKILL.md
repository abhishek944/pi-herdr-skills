---
name: agent-review
description: "Repository-agnostic independent review closeout for code changes or visual evidence, using correctness, architecture or contract, and regression perspectives with repeated review until clean. Requires Herdr-hosted Pi reviewers and blocks when that normal path is unavailable. Use before commit or ship."
compatibility: Requires a Git repository, Herdr, and Herdr-hosted Pi agents.
---

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

## Shared model-routing gate

Before creating reviewer runtime resources, load and follow the globally installed `model-routing-policy` skill. Resolve each reviewer responsibility from the Pi-global versioned catalog and preserve the resolution artifact. Every launch must pass the selected provider, model, and thinking level explicitly and verify all three against the runtime start response before prompting.

Resolve review models with `task_class: review`, the real input modalities, and every implementation contributor's model and thinking baseline. Use the policy's explicit no-contributor mode only for human-authored or direct work with no agent contributor. The shared resolver also captures the current caller. Use three fresh reviewer instances that are no weaker than the caller and every contributor in review capability and thinking, and strictly stronger than the combined ceiling in at least one dimension. If no such catalog choice exists, the review is blocked. Reviewer prompts must keep recursion disabled. Missing availability or an unverifiable launch is also a blocker.

## Runtime

Herdr-hosted Pi agents are the only reviewer runtime. Require `HERDR_ENV=1`, the `herdr` executable, a successful `herdr pane current --current`, and verified Pi-agent support. Do not probe availability by starting an agent in an existing pane. Actual Pi-agent startup happens only in the owned review tab. Any setup, launch, prompt, wait, or collection failure requires owned-tab cleanup and a blocked review.

Herdr agent kind is fixed to Pi. Do not substitute another agent kind or runtime. Provider, model, and thinking selection vary only through a verified catalog resolution. Every review uses three independent reviewers.

## Herdr review wave

Follow the globally installed `herdr` skill and this ownership protocol for every Herdr wave:

1. Capture the caller's workspace and current pane from Herdr's JSON response. Create one **dedicated, unfocused tab** in that workspace with the repository root as its working directory, a unique review label, and `--no-focus`. Parse and record `.result.tab.tab_id` and `.result.root_pane.pane_id`; never predict IDs.
2. Treat that tab ID as owned by this wave. The root pane belongs to reviewer one. Split panes inside that tab with explicit recorded pane IDs, the repository root as `--cwd`, and `--no-focus` until there is exactly one pane for each reviewer. Parse every new `.result.pane.pane_id` from JSON. Before starting agents, use `herdr pane rename` on the root and split panes with distinct responsibility names such as `correctness-safety`, `architecture-integration`, and `regression-fix-quality`; pane names are mandatory.
3. Start one uniquely named Pi agent in each named pane with the Herdr skill's mandatory `--kind pi`, passing that reviewer's resolved `--provider`, `--model`, and `--thinking` Pi arguments after `--`. Save each complete start response and verify it through the shared model-routing policy before prompting. Start **all** reviewer agents before any review wait begins. Do not focus the review tab.
4. After every agent has started, launch all three isolated `herdr agent prompt <name> <prompt> --wait --timeout <same-deadline>` commands concurrently, with a shared deadline of at least `900000` milliseconds (15 minutes) and separate output/error capture. Each command submits its prompt and observes the required lifecycle change before waiting for a settled state, avoiding an idle-before-work race. Join the prompt-and-wait processes as a group rather than serially. A blocked, timed-out, unknown, stalled, or failed reviewer is not a clean result.
5. Collect every result with `herdr agent get` and `herdr agent read --source recent-unwrapped`, preserving each reviewer's output separately. If a complete response cannot be recovered, block the review.
6. After outputs and failure evidence are safely collected, close **only** the exact recorded tab with `herdr tab close <created-tab-id>`. Also do this cleanup after partial startup, prompt, or wait failure. If closing fails, inspect the error and make a bounded retry against that same recorded ID only. Record and report any still-open owned tab as a cleanup blocker; do not issue a clean verdict while it remains open. Never close the caller's tab, an existing tab, a whole workspace, or a tab inferred from focus or position. If tab creation never returned an owned tab ID, close nothing.

Record the created tab ID, reviewer names, pane IDs, concurrent prompt-and-wait results, output locations, and cleanup result in the wave state. Starting every agent first and then running all `prompt --wait` calls concurrently is required; three sequential `prompt --wait` calls or separate no-wait prompts followed by immediately settled `agent wait` calls do not satisfy this workflow.

## Review mode, scope, and state

Choose exactly one mode:

- **Code mode:** determine the base ref and commit, target ref or working tree, included paths, and diff fingerprint. Use `<skill-root>/scripts/review-fingerprint.sh` when its Git assumptions fit.
- **Visual-evidence mode:** require a visual contract, current screenshots or recording, measured geometry, viewport and interaction state, and visible outcome or persistence evidence. Fingerprint the complete evidence package by content digest. Reviewers grade that package against the visual contract; a Git diff is not required.

Do not mix modes or silently switch modes. Missing required evidence blocks the review.

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

1. **Correctness and safety** — logic, authorization, security, data integrity, error handling, edge cases, idempotency, concurrency, and types.
2. **Architecture and integration** — ownership, established patterns, callers, contracts, configuration, migrations, documentation accuracy, and cross-component impact.
3. **Regression and fix quality** — realistic failure modes, compatibility, performance, test gaps, operational impact, and whether the change solves the underlying class rather than one example.

In visual-evidence mode:

1. **Visual correctness** — fidelity, hierarchy, typography, spacing, color, states, and responsive geometry.
2. **Contract and interaction** — approved decisions, controls, primary-action outcome, disabled and error states, and accessibility.
3. **Visual regression quality** — viewport matrix, theme coverage, persistence evidence, realistic edge states, and whether accepted defects are resolved.

Each reviewer must inspect the selected mode's complete evidence directly, remain read-only, avoid spawning agents, and return only actionable findings with severity and precise evidence locations, or clearly state that the perspective is clean.

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
- repository and external grounding performed;
- perspectives completed, their independence, and verified reviewer strength;
- checks run;
- accepted, rejected, and unresolved findings;
- fixes applied and rechecked;
- review-tab cleanup result, including any still-open owned tab blocker;
- final fingerprint and clean or blocked verdict.
