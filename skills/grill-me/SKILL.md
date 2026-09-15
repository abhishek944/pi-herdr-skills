---
name: grill-me
description: "Stress-test a plan or design one decision at a time and record the resulting shared understanding."
compatibility: Requires a repository checkout. A browser is optional for visual explanations.
---

# Grill Me

Challenge a plan before implementation. Ask one meaningful decision question at a time, explain why it matters, and record the answer.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Session coordination

When available, use `WorkCreate`/`WorkUpdate` and `TodoCreate`/`TodoUpdate` to keep the relevant session work and todos current. Use `MonitorCreate` only for a long-running background command and `LoopCreate` only for a future or repeated wake. Never change works, todos, loops, or monitors during `/ask` or `/btw`.

## Rules

- Ground factual questions in repository or external evidence before asking the user.
- Ask only for genuine product or engineering judgment.
- Put the recommended option first and explain its tradeoff.
- Offer a small set of distinct options plus a free-form answer.
- Keep one branch open at a time. Continue after each answer without asking the user to type `continue`.
- Use a simple diagram or HTML page only when it materially improves understanding.
- Keep unresolved choices open or explicitly deferred. Do not invent consensus.
- Do not edit production files.

## Workflow

1. Choose a short feature name and create the details folder.
2. Record the goal, scope, constraints, success criteria, and initial decision branches.
3. Ask the highest-priority open question in chat.
4. Record the user's answer and rationale immediately.
5. Add follow-up branches created by that answer.
6. Repeat until every branch is resolved or deferred.
7. Summarize the implementation contract and ask whether to proceed.

## Files

Write all interview material only under:

```text
var/<feature-name>/grill-me-details/
```

Keep it simple: `decision-tree.md`, optional `question-<n>.html`, and optional `response-<n>.md`.

## Final response

Summarize shared understanding, resolved decisions, deferred decisions, evidence, remaining risks, the decision-tree path, and the suggested next workflow.
