---
name: design-council
description: "Read-only design deliberation for architecture, API, data-model, workflow, or product decisions."
compatibility: Requires a repository checkout and support for independent agents when useful.
---

# Design Council

Compare design options without changing production files.

Before replying to the user, follow the global `talk-human` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Read project instructions and relevant architecture records first.
- For module, interface, or abstraction decisions, read the global `codebase-design` skill fully. Use its design contract and comparison checks within this workflow; it does not authorize implementation or require extra agents.
- Keep production files read-only.
- Ground repository claims in current files and external claims in reliable current sources.
- Use independent perspectives only when they add distinct evidence.
- Keep positions separate until synthesis and do not manufacture consensus.
- Stop after a recommendation; implementation is a separate workflow.

## Workflow

1. Define the decision, constraints, options, success criteria, and reversibility.
2. Gather repository, runtime, and external evidence.
3. If evidence gives one clear answer, explain it without creating a council.
4. Otherwise compare the smallest useful set of perspectives, such as product, architecture, security, operations, cost, or maintainability.
5. Synthesize the tradeoffs, rejected options, assumptions, dissent, and evidence that could change the recommendation.
6. Ask the user to approve the direction before implementation.

## Optional diagram handoff

When competing architectures, workflows, or state models are easier to compare visually, read and follow the global `archify` skill. Pass the feature name, decision, distinct options, verified current-source evidence, and assumptions. Keep the source-backed current-state diagram separate from each proposed option. Proposed diagrams must be description-backed, clearly labeled proposals without `meta.repository` or citations asserting unimplemented behavior; retain current-source evidence and assumptions in the decision notes. Preserve differences and uncertainty instead of implying consensus. Reuse the current work and todo; keep diagram artifacts under `var/<feature-name>/archify-details/` and link them from the decision notes. Archify does not choose the design or authorize implementation. Keep ordinary tradeoff tables and narrative reports in `visual-explainer`.

## Files

When notes should be retained, write only under:

```text
var/<feature-name>/design-council-details/
```

Use simple readable files such as `brief.md`, `perspectives.md`, and `decision.md`. Do not create runtime logs or machine state.

## Final response

State the recommendation, why it is preferred, alternatives, unresolved dissent, assumptions, risks, and an implementation handoff.
