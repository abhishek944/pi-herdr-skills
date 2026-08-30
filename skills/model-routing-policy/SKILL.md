---
name: model-routing-policy
description: "Shared catalog-based policy for every global workflow that launches an independent Pi agent. Resolves one explicit provider, model, and thinking level, then verifies runtime availability and launch provenance without alternate execution paths."
compatibility: Requires Python 3, Pi, and the bundled Pi-global model catalog at `~/.pi/agent/skills/model-routing-policy/models.json`.
---

Resolve `<skill-root>` to the directory containing this `SKILL.md`. This skill is a launch gate, not an agent runtime.

## User-facing language

Before every commentary or final response, read `../plainspoken-responses/SKILL.md`.

# Model Routing Policy

Use this policy before **every** Herdr-hosted independent-agent launch made by a globally installed skill. A launch without an explicit catalog resolution is forbidden.

## Invariants

- Use the single bundled Pi-global model catalog at `~/.pi/agent/skills/model-routing-policy/models.json`. Do not use a repository copy, dependency, generated file, or remembered default.
- Match structured catalog fields only. Do not choose a model by phrase-matching `bestFor` prose or by hard-coded model names.
- Resolve and persist the caller's actual provider/model/thinking settings plus the selected provider, model ID, thinking level, catalog path and digest, task class, required inputs, availability evidence, selection reason, and reviewer-escalation result before launch.
- Pass provider, model, and thinking level explicitly to Pi. Never omit one and inherit a runtime default.
- Each responsibility gets one immutable launch intent and one Herdr start attempt. Any failure blocks that responsibility after cleanup.
- Verify the actual launch settings. A started agent whose provider, model, or thinking level cannot be proven is failed launch infrastructure, not productive work.
- If resolution or launch fails, clean up owned resources and stop with a blocker. Do not retry with another model or runtime.
- Reviewer agents never launch more reviewers. Reviewer recursion remains disabled.

## Task classes

Use the narrowest class matching the responsibility:

- `coordination` — conductor work that may integrate several outcomes
- `architecture` — system, API, data-model, or workflow decisions
- `implementation` — multi-step production changes
- `exploration` — repository, runtime, data, or external evidence gathering
- `focused-edit` — small bounded code or documentation changes
- `multimodal` — work requiring image, audio, video, or PDF input
- `integration` — reconcile independently produced changes
- `review` — read-only correctness, architecture, regression, or adversarial review

The workflow supplies the class and required input types. The resolver uses catalog capability metadata and the structured `routing.reviewTier` rank; it never infers class from prompt wording.

## Resolve before creating runtime resources

1. Find the catalog and run:

   ```bash
   python3 <skill-root>/scripts/model-routing.py validate --catalog ~/.pi/agent/skills/model-routing-policy/models.json
   ```

2. Resolve each distinct responsibility before creating a Herdr pane or agent session:

   ```bash
   python3 <skill-root>/scripts/model-routing.py resolve \
     --catalog ~/.pi/agent/skills/model-routing-policy/models.json \
     --task-class <class> \
     --input text \
     --output <ignored-artifact>.json
   ```

   Add `--input image`, `--input pdf`, or another required modality as needed. The resolver always captures the current caller from Pi. For review, repeat `--stronger-than provider/model --stronger-than-thinking level` for every implementation contributor in scope. Use `--no-contributor` only when the reviewed work had no agent contributor and the current caller is the sole baseline.

3. Read the JSON result. Do not launch unless `launchAllowed` is true. Preserve the result as workflow evidence. Implement workflows use the emitted `stateSelection` object directly instead of hand-converting field names.

4. If the selected model cannot start, stop, clean up owned resources, and report the blocker. Do not select another model.

## Reviewer escalation

Review resolution compares against the current caller and every contributor being reviewed. The effective baseline is the highest review-capability tier and highest thinking level across all baselines. A reviewer qualifies as stronger only when it is no weaker on either dimension and strictly stronger on at least one:

```text
selected review capability >= baseline review capability
selected thinking          >= baseline thinking
at least one comparison is strictly greater
```

- `reviewerEscalation.status: "stronger"` means the selected reviewer passed that comparison.
- Provider outage, missing input capability, unavailable authentication, or no stronger reviewer is a launch blocker.
- Crossed or uncalibrated comparisons are not silently treated as stronger.

Independent reviewer instances and stronger reviewer models are separate requirements. A stronger model does not make a reused session independent.

## Explicit launch and verification

For Herdr, pass the resolver's Pi arguments after `--`:

```bash
herdr agent start <name> --kind pi --pane <pane-id> -- \
  --provider <provider> --model <model-id> --thinking <level>
```

Hash and preserve the resolution before launch. Save the complete start response,
then verify both artifacts:

```bash
python3 <skill-root>/scripts/model-routing.py verify-launch \
  --resolution <resolution.json> \
  --resolution-digest <pre-launch-sha256> \
  --herdr-start <start-response.json>
```

A runtime-environment probe is supplementary: pass its `provider`, `model`, and `thinking` through `--runtime-env`. The verifier recomputes the complete routing decision and requires every source to agree.

Record immutable session identity separately from model settings. The required launch provenance is:

- caller and contributor baseline provider, model, and thinking levels;
- selected provider, model, and thinking level;
- launched provider, model, and thinking level;
- catalog version, path, and digest;
- resolver artifact path and digest;
- availability evidence;
- runtime start response and immutable session identity;
- verification verdict;
- reviewer-escalation result.

## Failure behavior

Stop before prompting the agent when catalog validation, availability, explicit launch, or provenance verification fails. Clean up only exact resources owned by the workflow. Do not retry, substitute another model or runtime, lower thinking, or continue the independent workflow directly.
