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
- Use one dedicated tab and its root pane per delegated agent. Do not split agent tabs.

## Delegated agents

1. Choose a Pi model for the responsibility. As optional defaults, prefer `openai-codex/gpt-6-luna` at `max` thinking with `--fast` for implementation and other non-review work, and `openai-codex/gpt-6-sol` at `high` thinking without `--fast` for review or critique. If the current user explicitly requests another model, use that model instead; honor any requested provider, thinking level, or speed setting too. Check availability and required input support. If the optional default Fast setting is unavailable, omit `--fast` rather than blocking the work; if the user explicitly requested Fast, report that it is unavailable. Do not silently replace an explicitly requested model if it cannot be used.
2. Create a dedicated unfocused tab in the correct working directory for this agent. Read the returned tab and root-pane IDs; do not split the tab.
3. Give the root pane a short descriptive name.
4. Check `herdr pane process-info` until the pane has an interactive shell and no foreground command. Keep the wait bounded; do not use a sleep loop.
5. Start the agent with `herdr agent start <name> --kind pi --pane <id> -- --provider <provider> --model <model> --thinking <level> [--fast]`. Pass `--fast` only when chosen and supported; it requires the global `@calesennett/pi-codex-fast` Pi extension. For the standard-speed review default, omit it.
6. Verify the returned provider, model, thinking level, and requested Fast status before prompting.
7. Prompt with `--wait --timeout 900000` or longer for productive work.
8. Read the complete result, handle approval prompts with the user, and close only resources created for this work.

For parallel agents, create one dedicated unfocused tab per agent and use only each tab's root pane. Start and prompt them concurrently when useful; close only the tabs created for this work after collecting their results.

## Files

When durable notes are useful, write only under:

```text
var/<feature-name>/herdr-details/
```

Keep only a readable assignment and result summary.

## Final response

Report the work performed, agent outcomes, blockers, and confirmation that owned Herdr resources were closed.
