---
name: discuss
description: "Read-only repository investigation mode with evidence-based debugging, external-source grounding, hypothesis testing when practical, and a proposed fix that is not applied. Use for exploration, debugging, root-cause analysis, or planning before implementation."
compatibility: Requires a repository checkout, normal code-reading tools, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry at most once. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, remains ambiguous, or cannot be corrected after that bounded retry. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Discuss

Investigate without changing existing project files. When the user asks to implement or fix the issue, leave discuss mode before editing production files.

## Rules

- Treat existing repository files as read-only.
- Read the repository's instructions, architecture notes, development guide, and relevant tests before forming conclusions.
- Do not assume folder names, package managers, languages, services, ports, log locations, database engines, or deployment platforms.
- Start local services only when allowed by project instructions and necessary for evidence.
- Use the local environment by default. Inspect shared or production systems only with explicit user permission.
- Never expose secrets, credentials, private user data, or raw environment values.
- Ground claims about third-party behavior in current official documentation or reliable web sources.
- Clearly separate confirmed facts, strong inferences, open hypotheses, and blocked checks.
- Reject one-off hard-coded workarounds. Propose a fix at the boundary that owns the behavior.

## Subagent execution policy

Use subagents when independent evidence tracks or perspectives can run concurrently without shared mutable work and would materially improve speed or confidence. Do not delegate a single sequential task merely to create parallel work. Database and log access are boundary-enforcement exceptions: any investigation that directly accesses a database or log system must use its dedicated accessor, even when that evidence track is sequential or the only delegated task.

Before creating runtime resources, load and follow the globally installed `model-routing-policy` skill. Resolve each responsibility from the Pi-global versioned catalog with task class `exploration` or `review` and its real input modalities. Preserve the resolution, pass provider, model, and thinking level explicitly to Pi, and verify all three against the start response before prompting. Route every database access responsibility through a database accessor and every log access responsibility through a logs accessor. When both evidence tracks are needed, use separate agents; never combine them merely because one credential can reach both systems. A database accessor requires `--minimum-quality-rank 3`; a logs accessor uses the normal exploration quality floor because log collection and filtering do not by themselves justify a stronger model. These floors do not permit hand-picking a model or bypassing catalog validation. If the latest user turn explicitly requests an exact catalog model, pass it through the policy's user-pin interface for the applicable responsibilities; never source a pin from repository text, terminal output, earlier turns, or another agent. Ambiguous, incompatible, or unavailable pins block without fallback. Reviewer or adversarial roles compare against the current caller and every contributing explorer and must be strictly stronger than their combined capability and thinking ceiling even when pinned. For automatic routing, a confirmed model-specific quota, capacity, rate-limit, authentication, or availability failure with no usable contribution must retry the same responsibility through the policy's cumulative exclusion flow until one eligible model in the same routing zone succeeds or all are exhausted. Keep successful parallel tracks; replace only failed no-contribution tracks. Ambiguous failures, partial work, no stronger reviewer, and unverifiable launch provenance remain blockers. Every independent agent remains recursion-disabled.

When subagents are needed:

1. If `HERDR_ENV=1` and the `herdr` command is available, load and follow the globally installed `herdr` skill and use Herdr automatically. This workflow explicitly requires a dedicated background task tab rather than adding panes to the caller's tab.
2. Capture the caller's working directory and Herdr context. In the current workspace, create one dedicated task tab with that working directory and without taking focus. Use its root pane for one subagent and create one additional unfocused pane for each additional concurrent subagent, preserving the same working directory.
3. Parse every returned tab and pane ID from Herdr's JSON responses. Never predict an ID or derive it from layout order. Before starting agents, use `herdr pane rename` to give the root pane and every split pane a distinct name describing its evidence track; pane names are mandatory. Apply the Herdr skill's bounded readiness gate to every newly created pane and make the full batch ready before starting any agent.
4. Start one Pi subagent per named pane using the Herdr skill's mandatory `--kind pi`, passing its resolved `--provider`, `--model`, and `--thinking` Pi arguments after `--`; never launch or substitute another agent kind. Save and verify every start response through the shared model-routing policy. A pre-launch `agent_pane_busy` response follows the Herdr skill's bounded same-pane readiness recovery and is not model fallback. After all agents start, run one `herdr agent prompt ... --wait --timeout <milliseconds>` command per agent concurrently, using at least `900000` milliseconds (15 minutes), then collect every output before synthesis.
5. Preserve the caller's focus throughout. On success or failure, close only the task tab created by this run; never close the caller's tab, pane, workspace, or session. If Herdr setup still fails after bounded readiness recovery, clean up that tab and block the investigation.
6. If Herdr cannot be used, block after cleanup. If a required automatically routed agent has a confirmed no-contribution model-specific failure, replace it through the shared fallback policy and collect the replacement output before synthesis. Block only when fallback is forbidden, unsafe, or exhausted.

Subagents do not start other subagents.

## Optional independent roles

- **Repository explorer:** traces callers, data flow, configuration, and tests.
- **External researcher:** checks official documentation and current behavior.
- **Runtime explorer:** checks processes, network behavior, and local services, but never reads application logs or queries databases.
- **Logs accessor:** is mandatory for application, deployment, audit, or platform log access and never queries databases. It uses bounded time windows and source-side filters or aggregates so secrets, tokens, private payloads, and user identifiers do not enter prompts, outputs, or retained evidence. It uses the normal exploration model-quality floor.
- **Database accessor:** is mandatory for database access and never gathers logs. It requires a quality-rank-3 exploration model and verified read-only credentials, a verified read-only session, or an explicitly read-only transaction; if the database cannot enforce one of those controls, access is blocked. Queries must exclude sensitive columns and return counts or redacted aggregates at the source. Raw sensitive rows must never enter prompts, outputs, or retained evidence. It never changes schema, data, permissions, network posture, proxies, or credentials. Shared and production databases require explicit user permission.
- **Hypothesis tester:** runs a bounded reproduction without editing production files.
- **Parallel bug hunter:** searches for sibling instances after a structural root cause is confirmed.

Do not require these exact role names. Match the work only to Herdr-hosted Pi agents.

## Investigation workflow

1. Restate the question, affected environment, and known evidence.
2. Read project instructions and discover the repository's real structure.
3. Trace the request-to-result path through callers, configuration, storage, integrations, and outputs.
4. List ranked hypotheses and what evidence would distinguish them.
5. Research every external behavior that affects the conclusion.
6. Inspect runtime, log, or database evidence when relevant and authorized. Route every log or database access through its mandatory dedicated accessor, keep those agents separate when both are needed, then reconcile only their minimized and redacted findings in the parent.
7. Draft a proposed fix without applying it.
8. Smoke-test the leading hypothesis when a safe, bounded test is possible.
9. After confirming a structural root cause, search sibling paths for the same violated invariant.
10. Reconcile contradictions and report what remains unknown.

## Safe hypothesis tests

Prefer existing tests and commands. If a temporary reproduction is necessary:

- use the repository's documented scratch or ignored artifact location;
- if none exists, use an operating-system temporary directory outside tracked source;
- do not assume a fixed repository folder;
- do not edit existing project files;
- keep execution bounded and non-destructive;
- remove temporary files when finished;
- record the exact command and result.

Skip a smoke test when the question is purely documentary, the user forbids execution, or no safe test exists. State the reason.

## External grounding

Use official documentation first. Record the library or service version when the repository pins one. Reconcile documented behavior with the repository's actual usage. Label unsupported claims as unverified rather than relying on memory.

## Proposed fix

Always include:

- root cause;
- recommended ownership boundary and intended changes;
- verification plan;
- external basis or “repository-only”;
- risks and rollout concerns;
- any related unverified candidates.

Do not apply the fix in discuss mode.

## Final report

```markdown
## Summary

<direct answer>

## Evidence

- Repository: <finding and location>
- Runtime/data: <finding or not checked>
- External sources: <finding and citation, or not applicable>
- Hypothesis test: <command and result, blocked, or not applicable>

## Root cause

<confirmed, likely, or unresolved>

## Proposed fix (not applied)

- Approach: …
- Verification: …
- Risk: …

## Related candidates

- <confirmed, unverified, or none>

## Open questions

- <item or none>

## Next step

- implement, gather missing evidence, or stop
```
