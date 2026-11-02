---
name: model-routing-policy
description: Choose model, thinking level, and fast mode before launching subagents.
---

# Model Routing Policy

Apply only to subagents, not the parent agent.

| Responsibility | Model | Thinking | Fast |
| --- | --- | --- | --- |
| Production database access | openai-codex/gpt-6.1-sol | high | off |
| All subagents in `grill-me` and `ui-ux-grill-me` sessions, regardless of responsibility | openai-codex/gpt-6.1-sol | high | off |
| All subagents in `ui-ux-testing` sessions, including audit, component consistency, source investigation, synthesis, implementation and regression | openai-codex/gpt-6.1-sol | medium | off |
| Implementation, research, exploration, design, other non-review work | opencode-go/deepseek-v4.1-flash | max | off |
| Review and critique | openai-codex/gpt-6.1-sol | high | off |

- Production database access takes precedence over every other rule here, including the `grill-me` and `ui-ux-grill-me` session rule.
- Production database access means the subagent runs or authors queries, migrations, schema or data changes against a production database, or debugs production data. Local, development, and staging databases do not count.
- The `grill-me` and `ui-ux-grill-me` session rule takes precedence over the `ui-ux-testing` rule and responsibility-based defaults, including for ordinary non-review subagents.
- The `ui-ux-testing` session rule takes precedence over generic implementation/research and review/critique defaults for every worker assigned to its audit → fix → regression workflow. Production database access and enclosing `grill-me`/`ui-ux-grill-me` sessions still use their higher-priority rules.
- Explicit user choices override these defaults.
- If a subagent malfunctions, stalls, stops unexpectedly, gives incorrect responses, or produces poor-quality work, feel free to replace it or switch its model, while respecting explicit user choices and the production database access requirement.
- Check model availability before launching.
- If the chosen model is unavailable, report the blocker. Do not silently substitute another model.
