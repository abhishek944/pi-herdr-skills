---
name: model-routing-policy
description: "Choose explicit provider, model, and thinking settings for Pi agents launched by global workflows."
compatibility: Requires Pi and the global model catalog at `~/.pi/agent/skills/model-routing-policy/models.json`.
---

# Model Routing Policy

Use this policy before every independent Pi-agent launch. This policy chooses settings; the `herdr` skill operates the runtime.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Default choices

Read the global `models.json` catalog and confirm the model is available in `pi --list-models`.

- Focused edit: prefer `openai-codex/gpt-5.6-terra` at `high` thinking.
- Other routine work: prefer `openai-codex/gpt-5.6-sol` at `high` thinking.
- Simple review: use a fresh `openai-codex/gpt-5.6-sol` instance at `high` thinking.
- Complicated review: use a fresh `openai-codex/gpt-6-astra` instance at `high` thinking.
- Astra outside review is reserved for exceptionally difficult debugging when concrete evidence shows Sol and Terra are insufficient.

Do not widen these choices merely because a preferred model is unavailable.

## Rules

- Honor an exact model request only when it appears in the user's latest turn and the catalog permits it for the task.
- Ask when a nickname or family name is ambiguous.
- Match the task type, required input types, and supported thinking level from catalog fields.
- Pass provider, model, and thinking explicitly to Pi. Never inherit runtime defaults.
- Verify the launch response matches all three values before prompting the agent.
- Reviewers must be independent from the work they review.
- Do not retry a user-pinned model with a different model.
- Automatic fallback is allowed only after a clear provider availability failure before any useful work or side effect. Keep the same task and requirements, clean up the failed agent, and choose another permitted catalog candidate.
- Ambiguous failures, partial work, missing launch proof, or exhausted candidates block the delegated task.

## Files

If a routing record is useful, write a short readable note only under:

```text
var/<feature-name>/model-routing-policy-details/
```

Record the responsibility and selected provider/model/thinking. Do not create resolver output, digests, availability snapshots, fallback chains, or launch-verification artifacts.

## Final response

When routing matters to the user, state the selected model and reason, or explain the exact blocker.
