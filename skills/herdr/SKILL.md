---
name: herdr
description: "Control Herdr when the user explicitly requests it or another global skill selects it for Pi subagents. Requires HERDR_ENV=1."
---

# Herdr

Use Herdr only when the user names it or another active global skill explicitly chooses it for delegated Pi agents.

Before replying to the user, follow the global `plainspoken-responses` skill.

## Rules

- Confirm `HERDR_ENV=1` before controlling the current Herdr session.
- Learn command syntax from `herdr --help` and the relevant command group.
- Read every workspace, tab, pane, and agent ID from command output. Never guess IDs.
- Use `--current` or an explicit ID instead of relying on UI focus.
- Use `--no-focus` for background work.
- Never close a resource you did not create unless the user explicitly asks.
- Skills running inside Pi start only Pi agents and always pass provider, model, and thinking explicitly.
- Keep at most four panes in a tab. Use a new tab for additional work.

## Delegated agents

1. Read the global `model-routing-policy` skill and choose an allowed model.
2. Create an unfocused tab or pane in the correct working directory.
3. Give every pane a short descriptive name.
4. Check `herdr pane process-info` until the pane has an interactive shell and no foreground command. Keep the wait bounded; do not use a sleep loop.
5. Start the agent with `herdr agent start <name> --kind pi --pane <id> -- --provider <provider> --model <model> --thinking <level>`.
6. Verify the returned launch settings before prompting.
7. Prompt with `--wait --timeout 900000` or longer for productive work.
8. Read the complete result, handle approval prompts with the user, and close only resources created for this work.

For up to four parallel agents, use one dedicated tab: root pane, split root right, split root down, then split the right pane down. Larger batches use additional tabs in groups of four.

## Files

When durable notes are useful, write only under:

```text
var/<feature-name>/herdr-details/
```

Keep only a readable assignment and result summary.

## Final response

Report the work performed, agent outcomes, blockers, and confirmation that owned Herdr resources were closed.
