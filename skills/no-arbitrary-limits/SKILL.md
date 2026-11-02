---
name: no-arbitrary-limits
description: Apply to every implementation, fix, refactor, migration, and maintenance task. Prevent unrequested application capacity limits and mid-implementation limit questions; enforce only verified mandatory SDK/platform constraints or explicit user requirements, and explain optional limits after completion.
---

# No Arbitrary Limits

Apply this to every implementation, fix, refactor, migration, and maintenance task, including delegated work.

Before replying to the user, follow the global `talk-human` skill.

## Rule

Do not introduce or tighten application capacity limits unless the user explicitly requests them. Do not interrupt implementation to propose, negotiate, or ask for optional limits. Complete the authorized work without adding those restrictions, then explain relevant optional controls in the final handoff.

This includes byte/file/body sizes, item/file/row/cell counts, quotas, pagination ceilings, token/output caps, timeouts, concurrency caps, queue depth, cache/admission budgets, and similar restrictions. Do not hide them in schemas, validators, constants, SDK options, UI controls, infrastructure configuration, or generated code.

General requests such as "make it safe," "production-ready," "robust," or "optimize it" do not authorize arbitrary numeric caps. Neither an agent-authored plan nor a suggested value becomes user approval by being written down.

## Mandatory constraints

- Implement constraints genuinely required by the installed SDK, protocol, provider, or runtime platform. Verify their exact version, scope, units, and enforcement using installed documentation/source or official documentation, and preserve the evidence in normal task notes or the handoff.
- An optional SDK default, configurable timeout, example value, app-defined schema ceiling, conservative estimate, or guessed safety margin is not a mandatory constraint.
- Reuse existing streaming, chunking, or pagination support where appropriate instead of imposing a new whole-document/file ceiling because one transport frame is bounded. Do not expand scope into new infrastructure merely to avoid a limit.
- Do not add a stricter application cap than a mandatory boundary without the user's explicit requirement. Correctly account for required encoding/envelope overhead; do not invent an extra reserve.
- If a mandatory constraint makes the requested outcome impossible within the authorized design, report that concrete blocker immediately. Do not conceal it until completion, bypass it, or claim unsupported capacity. This exception does not authorize questions about optional caps.

## Existing behavior and safety

- Preserve existing limits unless the user authorizes changing them. This skill is not permission to silently remove, raise, or normalize old caps. Distinguish known user requirements from inherited limits with unknown rationale.
- Keep authentication, authorization, ownership, format/type validation, data-integrity checks, exact-revision/idempotency protections, cancellation, and required resource cleanup intact. Do not use this skill to bypass higher-priority safety requirements.
- "For safety" alone is not evidence for a new capacity quota. Keep essential validation separate from optional product restrictions and speculative memory/admission gates.
- When a capacity change is requested, trace producers, consumers, UI/server mirrors, schemas, encoders, storage, jobs, and deployment/runtime boundaries. Changing one constant does not prove the full path supports the new capacity.
- Do not silently truncate, resize, drop content, or retry consequential work to make an input appear to fit. Do not claim unlimited capacity; actual machine, SDK, provider, and model constraints still apply.
- Pass this rule to delegated agents and check their changes for unrequested limits before integration.

## Final handoff: optional limits, not implementation gates

After completing the authorized work, briefly report the relevant limits and optional places to impose controls:

- Mandatory SDK/platform constraints actually encountered, their sources, and what remains unverified.
- Existing limits preserved or explicitly user-requested limits implemented.
- Relevant optional controls left unapplied: the exact boundary where each could live, the concrete reason someone might choose it, and the capacity/performance/cost tradeoff. Mark any suggested value as a proposal, not an implemented or validated requirement.

Keep this proportional to the work; do not perform an unrelated whole-repository limit audit or invent optional controls just to fill a checklist. State when no optional limits were added. Do not make completion conditional on the user selecting optional limits.
