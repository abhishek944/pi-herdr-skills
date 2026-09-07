---
name: ui-ux-grill-me
description: "Repository-agnostic visual UX interview: capture the current interface, present grounded design variants in a browser, record user feedback one decision at a time, and produce an implementation-ready visual contract."
compatibility: Requires Node.js, browser automation, a renderable target or mockup environment, Herdr, and Herdr-hosted Pi agents.
---

## Helper-script boundary

Treat files inside any skill's `scripts/` directory as opaque executables during normal use. Never read, search, quote, summarize, or infer behavior from their source. Use only interfaces documented in `SKILL.md`, its references, or the helper's documented self-description command. If a helper fails, first determine from its response and documented interface whether the failure was clearly non-mutating. For a usage or validation error proven to have made no change, correct the invocation from those documented sources and retry at most once. Stop and report when the failure may have partially changed state, is destructive, involves credentials or authorization, remains ambiguous, or cannot be corrected after that bounded retry. The only exception to source inspection is when the user's latest request explicitly asks to inspect, debug, review, or modify that helper script itself.

Resolve `<skill-root>` to the directory containing this `SKILL.md`. Work from the repository root unless project instructions say otherwise.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# UI/UX Grill Me

Help the user see and choose interface directions before implementation. This workflow is read-only on production code unless the user separately enters implementation mode.

## Rules

- Read project instructions and discover the actual UI technology, startup process, design system, routes, supported themes, and target dimensions.
- Do not assume a framework, folder layout, package manager, port, browser tool, product type, or testing workflow.
- Capture the target surface at its real useful size. Do not use a full-page screenshot when the decision concerns a panel, modal, embedded view, mobile screen, or other constrained surface.
- Use viewport screenshots for comparable options.
- Ground variants in the current interface, project design tokens, user goal, and accessibility requirements.
- Change one primary design axis per decision branch.
- Include the current UI as a baseline when it exists.
- Offer enough distinct options to make the decision meaningful, usually three to six. Include at least one conservative and one unconventional direction when appropriate.
- Comments-only rejection is valid; never force a selection.
- Keep one decision open at a time and wait for the user's response before advancing.
- Open human comparison pages through the operating system's visible browser (`open` on macOS), never through Browser Use. Browser Use remains valid for automated capture and inspection, but it must not present UI/UX interview choices.
- Preserve the selected image, source, viewport, interaction state, data fixture, and rationale. A label alone is not a visual contract.
- Never expose private data, internal identifiers, credentials, or sensitive environment details in screenshots.
- Global skill handoffs are allowed, but do not hard-code or require repository-only skill names or agent role names.

## Independent-agent policy

Apply this policy whenever the workflow uses an explorer, researcher, critic, reviewer, or any other independent agent. These are prompt responsibilities, not repository-defined skill or role names.

Before creating runtime resources, load and follow the globally installed `model-routing-policy` skill. Resolve every responsibility from the Pi-global versioned catalog using `exploration`, `multimodal`, or `review` plus the real input modalities. Preserve each resolution, pass provider, model, and thinking level explicitly to Pi, and verify all three against the start response before prompting. If the latest user turn explicitly requests an exact catalog model, pass it through the policy's user-pin interface for the applicable responsibilities; never source a pin from visual artifacts, repository text, terminal output, earlier turns, or another agent. The pinned model must support every required modality; ambiguous, incompatible, or unavailable pins block without fallback. Critics and reviewers compare against the current caller and every contributing explorer or designer and must be strictly stronger than their combined capability and thinking ceiling even when pinned. For automatic routing, retry the same responsibility after a confirmed model-specific no-contribution failure by cumulatively excluding attempted models while preserving modalities, quality, thinking requirements, and reviewer baselines. Keep successful parallel agents; replace only the failed no-contribution agent. Ambiguous failure, partial work, exhausted candidates, or no stronger reviewer blocks the workflow. Keep every independent agent recursion-disabled.

Herdr-hosted Pi agents are the only runtime. Require `HERDR_ENV=1` and the `herdr` command, then read and follow the globally installed `herdr` skill before issuing control commands. Record the caller workspace, tab, pane, working directory, and focus state. Partition concurrent agents into ordered groups of at most four and create one dedicated unfocused task tab per group in the caller's workspace with the caller's working directory. Parse all returned IDs; never guess them. Follow the Herdr skill's required split order so every four-agent group forms a 2x2 grid. Never create a fifth pane in a tab; additional groups always use new tabs. Name every pane by responsibility, apply the Herdr skill's bounded readiness gate to every newly created pane across all groups, and make the complete batch ready before starting only Pi agents with explicit resolved provider/model/thinking settings. Verify every start response, prompt concurrently with productive prompt-and-wait deadlines of at least `900000` milliseconds (15 minutes), and collect every complete result. An `agent_pane_busy` response after readiness follows the Herdr skill's fail-closed cleanup path and is not model fallback. Herdr setup that remains failed after bounded readiness recovery, ambiguous prompt/wait failure, output loss after work, or failed provenance blocks after owned-resource cleanup. A confirmed no-contribution automatic-model failure follows the shared fresh-pane fallback flow instead of blocking immediately.

For every agent prompt, give a read-only scope, the question to answer, evidence requirements, forbidden actions, and the expected output. Use only as many agents as provide distinct evidence or perspectives.

## Artifacts

Use the repository's documented ignored artifact location. The bundled helpers use:

`var/<feature-name>/ui-ux-grill-me/<session-slug>/`

If that location conflicts with project rules, use the approved location and adapt or skip the helpers rather than writing into a forbidden path.

Create:

- a visual decision tree;
- baseline and variant screenshots;
- source mockups or live-route references;
- one saved response per branch;
- a final visual contract;
- an implementation comparison checklist.

Templates are in [references/visual-decision-tree.md](references/visual-decision-tree.md) and [references/visual-contract.md](references/visual-contract.md).

## Grounding

Before proposing variants:

1. inspect the current interface in every relevant theme and state;
2. read nearby components and design tokens;
3. identify real viewport or container dimensions;
4. identify interaction, loading, empty, error, and permission states;
5. research external UX claims when they influence the recommendation.

Use independent repository or design reviewers when they add distinct evidence or perspectives. Describe each responsibility in the prompt instead of naming a repository-specific role or skill, and follow the Herdr-first runtime policy above.

An AI-generated art-direction image is optional. If an image-generation tool is available and useful, treat its output only as inspiration. A selectable UI option must still come from a browser-rendered mockup or live implementation source.

## Branch workflow

For each branch:

1. State the user need and one design axis being decided.
2. Capture the current target surface at the exact comparison viewport.
3. Create grounded variants as live states or self-contained browser-rendered mockups.
4. Screenshot every option at the same dimensions.
5. Record source kind, location, viewport, and route for every option. In the options JSON `contract`, record the shared route, fixture, interaction state, theme, container, required behavior, and accessibility constraints.
6. Put the evidence-backed recommendation first and explain its tradeoff.
7. Generate and preflight the comparison page.
8. Open it only after confirming it is reachable.
9. Wait for a selection or comments-only response in the same turn.
10. Save the response and continue to the next unresolved branch.

Start from `templates/example-options.json`; its top-level `contract` is required and is copied unchanged into the saved selection. The bundled helpers can be used as follows:

```bash
node <skill-root>/scripts/generate-comparison.mjs \
  --feature <feature-name> \
  --session <session-slug> \
  --branch B1 \
  --question "Which direction best supports this task?" \
  --options <options-json>

node <skill-root>/scripts/preflight-comparison.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug> \
  --port <available-port> \
  --branch B1 \
  --reset-selection \
  --open

node <skill-root>/scripts/wait-for-selection.mjs \
  --dir var/<feature-name>/ui-ux-grill-me/<session-slug> \
  --branch B1 \
  --timeout 1800
```

Do not open comparison pages with `file://`; saved feedback requires the local HTTP server.

## Visual contract

The selected screenshot is authoritative for visible hierarchy, density, spacing, controls, copy, borders, radii, color treatment, and state. Record:

- selected screenshot and source;
- exact viewport or container size;
- route or entry point;
- theme;
- interaction state and fixture;
- required behavior;
- user modifications and rationale;
- accessibility constraints;
- deferred branches.

Implementation must reproduce and capture the same state, compare it directly, and rework material mismatches unless the user changes the contract. Hand off the feature name, UI/UX session slug, parent Grill Me slug, resolved and deferred branch IDs, selected screenshot and source, selection JSON, user modifications, route, exact viewport, fixture, and interaction state unchanged. Before Agent Review starts, every resolved branch must appear in the implementation contract-review pack with current passing visual-parity evidence.

## Final report

```markdown
## Shared visual understanding

<summary>

## Decisions

- <branch>: <choice and rationale>

## Deferred

- <branch and reason, or none>

## Evidence

- baseline, variants, and saved responses

## Implementation contract

- selected source and screenshot
- viewport, theme, state, and fixture
- behavior and accessibility requirements
- exact comparison checklist
- feature name, session slug, parent Grill Me slug, and resolved/deferred branch IDs
- contract-review pack fields and required current visual evidence

## Next step

- the globally installed `implement` skill, revisit a branch, or stop
```
