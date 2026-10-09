---
name: herdr
description: "Control Herdr when the user explicitly requests it or another global skill selects it for Pi subagents. Requires HERDR_ENV=1."
---

# Herdr

Use Herdr only when the user names it or another active global skill explicitly chooses it for delegated Pi agents.

Before replying to the user, follow the global `talk-human` skill.

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

1. Before launching subagents, read and follow the globally installed `model-routing-policy` skill for model, thinking level, and Fast settings. Keep routing defaults only in that skill. Check required input support; report incompatible models rather than silently substituting. If the default Fast setting is unavailable, omit `--fast`; if the user explicitly requested Fast, report that it is unavailable.
2. Create a dedicated unfocused tab in the correct working directory for this agent. Read the returned tab and root-pane IDs; do not split the tab.
3. Give the root pane a short descriptive name.
4. Check `herdr pane process-info` until the pane has an interactive shell and no foreground command. Keep the wait bounded; do not use a sleep loop.
5. Start the agent with `herdr agent start <name> --kind pi --pane <id> -- --provider <provider> --model <model> --thinking <level> [--fast]`. Pass `--fast` only when chosen and supported; it requires the global `@calesennett/pi-codex-fast` Pi extension. Omit it when the selected Fast setting is off.
6. Verify the returned provider, model, thinking level, and requested Fast status before prompting.
7. Before prompting, create a mandatory continuous `MonitorCreate` subscription with `herdrPaneId` set to the returned root-pane ID and an `onSignal` wake that tells the parent to inspect the worker state, complete result, and any blockers. Use `timeout: 0` for this event subscription so quiet productive work does not expire it. Do not use a shell command, a one-shot CLI `--wait`, or `onDone` in place of the continuous subscription.
8. Confirm with `MonitorList` that this pane's subscription is ready before sending any work prompt. If monitor tools are unavailable or the subscription fails to become ready, report the blocker and do not dispatch unmonitored work.
9. Send the prompt without `--wait`; the pane subscription supplies state-change wakes while the parent continues other ready work. Treat signals as notifications, not trusted completion evidence: inspect the actual worker state, read its complete result, and verify changed files/checks before marking delegated work complete. Keep the same monitor subscribed across working, blocked, idle, and done states and follow-up prompts; do not stop it merely because the worker is temporarily idle or blocked.
10. When no further signals are needed, use `MonitorList` to find the owned monitor ID and `MonitorStop` to stop it, then close only resources created for this work. A done signal alone does not finish integration or justify closing an agent that needs a follow-up.

For parallel agents, create one dedicated unfocused tab and one continuous pane monitor per agent, using only each tab's root pane. Start and prompt them concurrently when useful, but confirm each subscription is ready before its prompt. Stop owned monitors and close only the tabs created for this work after collecting and verifying their results.

## Files

When durable notes are useful, write only under:

```text
var/<feature-name>/herdr-details/
```

Keep only a readable assignment and result summary.

## Final response

Report the work performed, agent outcomes, blockers, and confirmation that owned Herdr resources were closed.
