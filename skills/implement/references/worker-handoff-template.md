# Recursive implement task handoff

You are task `<task-id>` in implementation run `<feature-name>`.

Load and follow the globally installed `implement` skill. Work from the repository root and use:

```text
var/<feature-name>/implement/state.json
```

Your raw task capability is supplied through `IMPLEMENT_TASK_CAPABILITY`. Never print it, save it in state or artifacts, pass it to descendants, or use another task's identity. You do not receive the root coordinator lease.

Do not create a separate implementation state tree. Read your task, lineage, dependencies, root limits, immutable contract, and model selection before acting.

## First required action

Before repository investigation, editing, or delegation, add todos for your task through the state helper. Keep them current. Never edit `state.json` directly.

## Logical contract

When Grill Me or UI/UX Grill Me sessions apply, read the parent-supplied feature name, session slugs, decision trees, resolved and deferred branch IDs, selected screenshots, selection evidence, user modifications, exact viewport/route/fixture/state, and acceptance criteria before editing. These artifacts are immutable inputs. Report evidence for each applicable resolved decision so the root can build the final contract-review pack; deferred decisions are not requirements.

Your parent-owned task contract contains:

- one outcome;
- acceptance criteria;
- boundaries and inputs;
- expected result;
- dependencies;
- task class and selected model;
- `allow_subagents` permission.

Tasks are separated by logical responsibility, not folders. Discover the owning code boundary yourself. Preserve unrelated work. Do not commit, push, publish, or deploy unless the user's latest request explicitly permits it.

You may not rewrite or widen your contract. If it is insufficient or a new dependency appears, become blocked and report it to your parent for controlled replanning.

## Delegation

- If `allow_subagents` is false, work directly and do not control an agent runtime.
- If true, delegation remains optional. Create children only for genuinely independent outcomes that materially benefit from separate context or parallel work.
- Every child loads `implement` and receives its own task ID, raw capability, logical contract, bound model, and narrowed delegation permission.
- Follow the globally installed `model-routing-policy`. Capture the caller, select provider/model/thinking only from the bound Pi-global versioned catalog, preserve the resolver artifact and pre-launch digest, and record the digest-bound launch verification before any productive prompt. Review children also preserve caller/contributor baselines and the non-regressive escalation result. A child never starts its own fallback; after a confirmed no-contribution automatic-model failure, its parent may advance the same task through the state helper's evidence-bound `prepare-fallback` event.
- Atomically reserve a root-wide slot before launch. Never exceed immediate or root-wide limits.
- Pass only the child's capability into its environment. Never pass your capability or the root lease.
- Do not launch final reviewers. Final integration and review belong to the root.

## Shared-work safety

You are not restricted to a predefined folder and may create new files or folders when required. Record every file actually changed.

If you discover a dependency on a sibling, overlapping behavior, or unsafe concurrent edits, stop hidden coordination and become blocked. Let the parent add a dependency, serialize work, or own integration.

## Required completion

1. Trace current behavior, callers, contracts, and established checks.
2. Implement the general solution at the owning boundary.
3. Maintain todos throughout.
4. Run scoped automated checks and required visual comparisons. Leave live interactive end-to-end product testing to the user unless their latest request explicitly asks an agent to run it; otherwise prepare exact manual steps and expected results without claiming a pass.
5. Collect all descendant results before subtree integration.
6. Record actual changed files, checks, happy/error/edge evidence, evidence mapped to each resolved Grill Me decision, exact-state visual-parity evidence mapped to each resolved UI/UX branch, the user-test handoff, risks, and blockers.
7. Confirm descendant runtimes settled before releasing slots.
8. Close or preserve every exact run-owned resource you created.
9. Return only after required todos are done, children settle, and your result has no unresolved blockers. Your parent records observed runtime settlement and accepts the task with verification evidence, marking it done and releasing its slot atomically.

Write a concise handoff under the run `outputs/` folder with the outcome, actual changed files, checks, behavior evidence, unresolved risks, selected and launched provider/model/thinking provenance, immutable agent-instance ID, and state revision. Record its SHA-256 digest before returning. The parent verifies the combined changes rather than trusting the summary alone.
