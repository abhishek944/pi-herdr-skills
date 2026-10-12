---
name: codebase-design
description: Design and review module responsibilities, interfaces, abstractions, and TypeScript/Effect contracts. Use before non-trivial interface changes or when reviewing coupling, scattered logic, dependency ownership, or unnecessary wrappers.
license: MIT
---

# Codebase Design

Hide meaningful complexity behind a small, explicit interface. Keep the knowledge needed to change a behavior together. More files, classes, services, layers, or generic types do not automatically make a better design.

This is a design reference, not a replacement for the global workflows. Read it fully when applicable. Follow `talk-human` before replying and `no-unit-tests` unless the latest user request explicitly asks for unit tests.

## Workflow boundaries

- Read repository instructions, relevant flow/architecture records, existing callers, and similar implementations first.
- In `research` or `design-council`, keep production files read-only. Design advice does not authorize implementation.
- In `implement`, work only within the approved scope and record the design in its existing plan, not a second task system.
- In `agent-review`, inspect the actual changes and callers against the agreed contract; reviewers remain read-only.
- Reuse the owning workflow's Work/Todo tracking and artifact directory. If invoked alone, follow the global coordination rules; optional notes belong under `var/<feature-name>/codebase-design-details/`.
- This skill does not authorize commits, deployment, dependency upgrades, live testing, or creating, editing, deleting, or running unit tests.

## Shared concepts

A **module** can be a function, service, class, or package with an interface and implementation. Its **interface** includes everything a caller must know: types, invariants, failure modes, ordering, configuration, resource ownership, and relevant performance limits. A **seam** is where behavior can be substituted; an **adapter** implements the contract at that seam.

A **deep module** provides substantial useful behavior through a small interface. Depth is caller leverage, not a ratio of implementation lines to interface lines. Keep valid repository and library terms such as API, boundary, and Effect service; do not rename them to enforce a glossary.

## Design checks

1. **Start with callers.** Show a realistic usage example. A contract that requires callers to understand implementation details is incomplete.
2. **Own the behavior once.** Put an invariant or policy at the boundary responsible for enforcing it, not in every caller or several pass-through layers.
3. **Keep knowledge local.** If understanding a behavior requires repeatedly opening tightly coupled siblings, combine or deepen them rather than adding another wrapper.
4. **Reduce interface burden.** Prefer fewer meaningful operations and simpler parameters. Do not merge unrelated capabilities just to reduce method count.
5. **Use the deletion check.** If removing a wrapper removes complexity, it was unnecessary. If complexity would spread across callers, it is earning its keep.
6. **Justify substitution.** Reuse existing capabilities and prefer plain functions for pure decisions. Add a port or service for a real external dependency, ownership/lifecycle requirement, policy boundary, or justified variation—not a hypothetical future.
7. **Keep internal seams internal.** Do not expose implementation collaborators merely to make them accessible to tests. Verification should observe the public contract.
8. **Make states explicit.** Model domain invariants and invalid states with appropriate types, schemas, constraints, or discriminated unions. Prefer ordinary types and built-in utilities over clever generic machinery.
9. **Explain only what code cannot.** Put caller-visible guarantees next to the interface and surprising rationale near the implementation. Record durable, consequential trade-offs in the repository's existing decision format.

Two justified adapters are evidence for a useful seam, not a prerequisite. One implementation may still own a real dependency or resource lifecycle. Never invent a test adapter solely to justify an abstraction.

## Design contract before non-trivial changes

Before changing an interface, adding an abstraction, or restructuring responsibilities, write a short contract in the owning workflow's plan or decision notes:

- Goal, existing callers, domain invariants, and scope/non-goals.
- Module responsibilities, public TypeScript signatures, and one caller example.
- Success result, expected failures, required dependencies, and who handles each failure.
- Hidden implementation details, dependency/resource ownership, and why each new abstraction is needed.
- Ordering, concurrency, transactions, retries/idempotency, and cancellation where relevant.
- Compatibility, migration/rollback concerns, acceptance criteria, and allowed verification commands.

Scale this to the change. A local straightforward fix needs only a brief ownership/contract check, not a speculative architecture document. Surface meaningful uncertainty before coding. In design-council, stop at a recommendation and obtain direction approval; in approved implementation, pause only for a material unresolved scope or design decision.

## TypeScript and Effect

Apply these checks only when the repository uses Effect:

- Inspect the lockfile and installed Effect/TypeScript versions. Prefer the installed `effect/AGENTS.md` when present, then version-matched declarations, source, and official documentation. Do not upgrade dependencies or copy APIs from an unpinned upstream branch.
- Specify the success, expected error, and requirements channels of `Effect.Effect<A, E, R>`. Avoid accidental `any`/`unknown` in error or requirements contracts and unchecked casts that hide missing guarantees.
- Use Schema to validate untrusted data at trust boundaries. Use branded values or tagged variants when they enforce a real invariant, not mechanically for every primitive.
- Use Effect's installed service and Layer APIs for real dependency and lifecycle ownership; do not build a parallel DI framework. Keep pure domain decisions as plain functions when appropriate.
- Capture implementation dependencies when building a service Layer where appropriate, rather than leaking them through every method. Any remaining method requirements must be deliberate and documented.
- Keep expected domain failures typed. Translate foreign failures at adapters and decide explicitly which failures callers recover from versus propagate.
- Compose dependencies and execute effects at application/runtime boundaries. Avoid hidden runtime execution in domain logic; make any necessary interop boundary explicit.
- Define who acquires, shares, and releases resources. Use scoped acquisition and structured concurrency; bound input-sized parallel work and specify cancellation behavior.
- Retry mutations only with an explicit idempotency/duplicate-handling strategy. Define transactional ownership where partial failure matters.
- Verify through the repository's actual typecheck, lint, build, schema, and compatible Effect-diagnostic commands. Do not invent commands or add tooling without approval. Tests remain subject to `no-unit-tests`.

## Compare designs when uncertainty matters

For consequential interface decisions, compare at least two genuinely different designs: their caller examples, interface burden, hidden complexity, ownership, failure behavior, and cost of change. Include the simplest existing-pattern option. Prefer the design with clearer contracts and less distributed knowledge, not maximum flexibility.

Do this directly when evidence is sufficient. Independent perspectives are optional, not a mandatory three-agent exercise. If agents are useful, follow the global `design-council`, `model-routing-policy`, and `herdr` lifecycle, including required monitors and recursion limits. Do not launch agents just because a design checklist exists.

## Review and handoff

Check the actual code against the agreed contract and representative callers. Look for duplicated policy, shallow forwarding layers, hidden ordering requirements, invalid states, dependency leaks, unsafe retries, and unclear resource ownership. Preserve unrelated work and existing tests.

Report the chosen design, important rejected alternatives, remaining uncertainty, and actual verification or blocked checks. Do not claim that a written design or passing typecheck alone proves runtime correctness.

## Provenance

Adapted from Matt Pocock's [codebase-design](https://github.com/mattpocock/skills/tree/d80fa0f4ebe0c5714af0adf8670336065233ecc6/skills/engineering/codebase-design), including its deepening and alternative-design references, at `d80fa0f4ebe0c5714af0adf8670336065233ecc6` (MIT, Copyright (c) 2026 Matt Pocock). Local adaptations preserve repository terminology, proportionate delegation, workflow boundaries, test permissions, and version-aware Effect guidance. See [LICENSE](LICENSE).
