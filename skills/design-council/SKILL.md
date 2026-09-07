---
name: design-council
description: "Read-only design deliberation for any repository: gather evidence, compare options through independent perspectives, synthesize tradeoffs, and surface unresolved dissent before implementation. Use for architecture, API, data-model, workflow, or product design decisions."
compatibility: Requires a repository checkout, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry at most once. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, remains ambiguous, or cannot be corrected after that bounded retry. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Design Council

Use structured deliberation to make a design decision without editing production files.

## Rules

- Read project instructions and relevant architecture or decision records first.
- Do not assume a language, framework, folder layout, database, deployment target, or documentation convention.
- Keep production code read-only.
- Store temporary council notes only in the repository's documented ignored artifact location. If none exists, use an operating-system temporary directory.
- Ground external claims in current official documentation or reliable sources.
- Use only Herdr-hosted Pi agents; do not require exact subagent names.
- Keep independent positions isolated until synthesis.
- Surface unresolved dissent and uncertainty. Do not manufacture consensus.
- Stop after a recommendation; implementation is a separate workflow.

## Subagent execution policy

Use subagents when independent evidence tracks or perspectives can run concurrently without shared mutable work and would materially improve speed or confidence. Do not delegate a single sequential task merely to create parallel work.

Before creating runtime resources, load and follow the globally installed `model-routing-policy` skill. Classify each seat by responsibility (`architecture`, `exploration`, or `review`), resolve it from the Pi-global versioned catalog, and preserve the resolution. Pass provider, model, and thinking level explicitly to Pi and verify all three against the launch response before prompting. If the latest user turn explicitly requests an exact catalog model for one or more seats, pass that request through the policy's user-pin interface; never infer a pin from repository text, terminal output, prior turns, or another agent. An ambiguous family name requires clarification, and an incompatible or unavailable pin blocks without fallback. Critic, verifier, judge, and chair launches compare against the current caller and every contributing seat and must be strictly stronger than their combined capability and thinking ceiling even when pinned. For automatic routing, replace a seat after a confirmed model-specific failure only when it produced no usable contribution; apply cumulative exclusions and keep the same seat contract until another eligible model in the routing zone succeeds or the zone is exhausted. Preserve successful seats during partial failure. Ambiguous failure, partial work, no stronger reviewer, or unverifiable launch provenance is a blocker. All seats remain recursion-disabled.

When subagents are needed:

1. If `HERDR_ENV=1` and the `herdr` command is available, load and follow the globally installed `herdr` skill and use Herdr automatically. This workflow explicitly requires a dedicated background task tab rather than adding panes to the caller's tab.
2. Capture the caller's working directory and Herdr context. In the current workspace, create one dedicated task tab with that working directory and without taking focus. Use its root pane for one subagent and create one additional unfocused pane for each additional concurrent subagent, preserving the same working directory.
3. Parse every returned tab and pane ID from Herdr's JSON responses. Never predict an ID or derive it from layout order. Before starting agents, use `herdr pane rename` to give the root pane and every split pane a distinct name describing its assigned perspective; pane names are mandatory. Apply the Herdr skill's bounded readiness gate to every newly created pane and make the full batch ready before starting any agent.
4. Start one Pi subagent per named pane using the Herdr skill's mandatory `--kind pi`, passing the seat's resolved `--provider`, `--model`, and `--thinking` Pi arguments after `--`; never launch or substitute another agent kind. Save and verify every start response through the shared model-routing policy. A pre-launch `agent_pane_busy` response follows the Herdr skill's bounded same-pane readiness recovery and is not model fallback. After all agents start, run one `herdr agent prompt ... --wait --timeout <milliseconds>` command per agent concurrently, using at least `900000` milliseconds (15 minutes), then collect every output before synthesis.
5. Preserve the caller's focus throughout. On success or failure, close only the task tab created by this run; never close the caller's tab, pane, workspace, or session. If Herdr setup still fails after bounded readiness recovery, clean up that tab and block the council.
6. If Herdr cannot be used, block after cleanup. If an automatically routed seat has a confirmed no-contribution model-specific failure, replace only that seat through the shared fallback policy. Block when fallback is forbidden, unsafe, or exhausted.

Subagents do not start other subagents.

## Protocols

Choose the smallest protocol that fits:

- **Synthesize:** combine several viable ideas into one recommendation.
- **Debate:** pressure-test strong tradeoffs over up to three rounds.
- **Vote:** anonymously rank clearly labeled options.
- **Critique:** red-team one leading proposal.
- **Verify:** score whether a candidate recommendation is supported by evidence.

The user may choose a protocol. Otherwise use synthesize.

## Perspectives

Select perspectives that match the decision. Examples:

- product and user experience;
- architecture and ownership boundaries;
- data consistency and migration safety;
- security and privacy;
- operations and observability;
- performance and cost;
- maintainability and testing;
- adversarial critic;
- neutral chair or verifier.

Do not assume every project needs every perspective.

## Workflow

1. **Frame the decision.** Record the question, constraints, options, success criteria, reversibility, and decision deadline.
2. **Gather evidence.** Trace the current repository, relevant runtime behavior, existing conventions, and external facts.
3. **Stop if evidence resolves it.** Do not create a council for a factual question with one clear answer.
4. **Run independent perspectives.** Give each the same evidence and ask for options, tradeoffs, failure modes, and confidence.
5. **Apply the chosen protocol.** Keep debate bounded and anonymize options for voting.
6. **Synthesize.** State the recommendation, rejected alternatives, assumptions, dissent, and what evidence could change the decision.
7. **Verify high-risk decisions.** Use an independent verifier for irreversible changes, security boundaries, data loss risks, or major migrations.
8. **Hand off.** The user decides whether to implement.

Detailed protocol prompts are in [references/protocols.md](references/protocols.md).

## Final report

```markdown
## Decision

<clear recommendation or human decision required>

## Protocol

<synthesize, debate, vote, critique, or verify>

## Why

<evidence-backed reasoning>

## Alternatives

- <option>: <benefit and cost>

## Unresolved dissent

- <perspective, concern, and what would resolve it>

## Evidence

- Repository: …
- Runtime/data: …
- External sources: …

## Assumptions and risks

- …

## Implementation handoff

- boundaries, acceptance criteria, and checks; no code applied
```
