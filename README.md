# pi-herdr-skills

A portable collection of global [Pi](https://pi.dev/) skills for planning, implementation, review, browser and desktop work, visual explanations, and [Herdr](https://herdr.dev/)-hosted Pi agents.

> [!WARNING]
> Pi extensions run with your user permissions, and skills can instruct an agent to run commands. Review this repository and every extension you install before enabling it.

## Install the skills

First [install Pi](https://pi.dev/docs/latest/quickstart):

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

Clone this repository, inspect it, and run the conflict-safe installer:

```bash
git clone https://github.com/abhishek944/pi-herdr-skills.git
cd pi-herdr-skills
./scripts/install.sh --dry-run
./scripts/install.sh
```

The installer copies this repository's skills into the shared global `~/.agents/skills/` directory (discovered by Pi, Codex, and OpenCode). It does not require or install a permission extension or policy. It refuses to overwrite a different managed skill. If you intentionally replace conflicts, `./scripts/install.sh --force` backs up the existing files under `~/.pi/agent/skills-backups/` first.

Restart Pi, or run `/reload` in an existing Pi session. See the official [skills documentation](https://pi.dev/docs/latest/skills) for Pi's discovery rules.

### Update or remove

Update the checkout, inspect the diff, and reinstall:

```bash
cd pi-herdr-skills
git pull --ff-only
npm run check
./scripts/install.sh --dry-run
./scripts/install.sh --force
```

If you are updating from a version that included the retired `herdr-orchestrator` skill, the installer cannot discover that removed source directory. Inspect and back up any local changes, then remove its installed copy and reload Pi:

```bash
rm -rf -- "$HOME/.agents/skills/herdr-orchestrator"
```

If upgrading from `discuss` or `plainspoken-responses`, the installer does not remove their retired global directories. After inspecting and backing up any local changes, remove `~/.agents/skills/discuss/` and `~/.agents/skills/plainspoken-responses/` so Pi loads only `research` and `talk-human`. Reload Pi afterward.

`--force` creates a backup before replacing any locally changed skill. To uninstall matching copies:

```bash
./scripts/install.sh --uninstall --dry-run
./scripts/install.sh --uninstall
```

If an installed skill was modified, uninstall refuses to remove it unless you add `--force`; forced removal backs it up first.

## Included skills

| Skill | Purpose |
| --- | --- |
| `agent-review` | Uses one independent reviewer by default when warranted, focused on concrete defects in the requested behavior and affected callers. |
| `archify` | Renders and validates interactive architecture, workflow, sequence, data-flow, and state diagrams. |
| `awesome-logging-standards` | Guides structured application/error logs, redaction, request summaries, and TypeScript/Node.js or Effect integration. |
| `browser-use` | Automates browser navigation, forms, screenshots, testing, and extraction. |
| `commit-and-merge` | Commits real changes and merges into the default branch when explicitly requested. |
| `codebase-design` | Guides module responsibilities, explicit interfaces, justified abstractions, and version-aware TypeScript/Effect contracts. |
| `computer-use` | Operates desktop apps through local Cua Driver MCP with grounded input, screenshot forwarding, and verified outcomes. |
| `design-council` | Compares architecture, API, workflow, and product-design options without editing. |
| `firstmate` | Keeps a primary session in a coordinator role: conversation, decisions and quick inspection stay local while project execution is delegated. |
| `research` | Investigates and debugs a repository without applying a fix. |
| `security-audit` | Cloudflare's source-first security guidance and evidence-led audit workflow, with independent validation and structured reports. |
| `next-feature` | Autonomously recommends what to build next from real user problems, web evidence, product fit, and code-grounded sizing. |
| `grill-me` | Challenges a plan in DAG levels with parallel browser branch owners and recorded follow-ups. |
| `model-routing-policy` | Defines shared subagent model, thinking, and Fast defaults in one editable file. |
| `implement` | Coordinates every tracked Work with session/Work/Task artifact paths, self-versus-delegate decisions, checks, and proportionate review while preserving specialized scope. |
| `no-arbitrary-limits` | Prevents unrequested capacity caps and implementation-time questions about optional limits; reports optional controls after completion. |
| `no-unit-tests` | Prevents unit-test creation or execution unless the user explicitly requests it. |
| `talk-human` | Combines clear, friendly replies with Caveman's lite brevity. |
| `caveman` | Optional standalone concise response styles; bundled skill-only under Apache-2.0. |
| `read-flows` | Finds and reads repository flow documentation before relevant changes. |
| `retro` | Reviews a coding session for ways to improve the agent's working environment; invoke explicitly with `/skill:retro`. |
| `ui-ux-grill-me` | Captures an interface and resolves independent UX branches in parallel browser interviews. |
| `ui-ux-testing` | Audits UI/UX in parallel, implements validated in-scope fixes and reruns regression checks; honors explicit audit-only requests. |
| `visual-explainer` | Produces self-contained HTML explanations, diagrams, comparisons, and data views. |

`codebase-design` is the shared design reference for relevant `design-council`, `implement`, and `agent-review` work. It asks for a short design contract before non-trivial abstraction changes, without forcing extra agents or overriding test permissions. It is adapted from Matt Pocock's guidance; provenance and the MIT license are bundled with the skill. Run `/skill:codebase-design` to invoke it directly.

`security-audit` is adapted from [Cloudflare's MIT-licensed skill](https://github.com/cloudflare/security-audit-skill); companion guidance, schema, validators, license, and pinned provenance are bundled. Use `/skill:security-audit` for focused security guidance. Full audits require independent agents, Node.js, and an OS-enforced sandbox before executing target code. Full-audit reports use the parent's canonical task directory, and scratch/evidence ownership follows each worker's actual nested session/Work/Task directory. Keep validator ownership rules and sandboxed evidence promotion aligned with those roots; agent labels never replace task identity. Installing the skill does not run an audit or install sandbox tooling.

Some skills depend on other skills in this repository. Install the complete set rather than copying only `implement`, `agent-review`, or `design-council`.

The `herdr` skill and eight `Agent*` tools are now provided together by [pi-herdr](https://github.com/abhishek944/pi-herdr), not by this skill installer or pi-tasks. Install pi-herdr with the compatible pi-tasks source described in its README and pi-loop-monitor. Published pi-tasks 0.15.0 still registers the old Agent tools, so do not load it alongside pi-herdr. Before migrating, inspect and back up `~/.agents/skills/herdr/`; after verifying pi-herdr loads its bundled skill, remove the old global copy to avoid duplicate skill names. The installer does not automatically remove retired directories. Other managed skills remain here.

`implement`, the package-provided `herdr` skill, pi-tasks, pi-herdr, and pi-loop-monitor share a coordination contract: pi-tasks owns records/progress and timing, `implement` owns task ownership decisions and artifact paths, pi-herdr owns Agent tools/lifecycle, and pi-loop-monitor owns monitoring. Root task artifacts use repository-relative `var/<sessionId>/<workId>/<taskId>/`; delegated tasks append their own session/Work/Task IDs below the exact parent task directory. Obtain the full session ID from `PI_SESSION_ID` through the agent's own shell tool, require real tracking IDs before execution, and record paths and `self`/`delegate` reasons in `taskInfo`. This is instruction-only, not automatic enforcement or migration. All managed skills and their helpers use this same ownership contract. Specialized permissions, file formats and cleanup rules remain intact; feature names, interview slugs and lane labels are descriptive metadata, not alternative artifact roots. Existing artifacts are not moved implicitly.

Edit `skills/model-routing-policy/SKILL.md` to change subagent model, thinking, and Fast defaults. `implement`, `agent-review`, `herdr`, `grill-me`, and `ui-ux-grill-me` read that shared policy before launching agents. Explicit user choices override its defaults; the parent agent's model is unchanged. Reinstall after editing so the global copy stays current.

### Desktop computer use

`computer-use` uses Pi's native MCP with an independently installed official [Cua Driver](https://cua.ai/docs/cua-driver/quickstart). It does not install a computer-use extension, replace Pi's model, or invoke another agent. On macOS, after reviewing and installing Driver and approving its OS permissions, register the signed app executable globally:

```bash
pi mcp add cua-driver --exposure codemode -- /Applications/CuaDriver.app/Contents/MacOS/cua-driver mcp
pi mcp list
```

On other platforms, use the reviewed `cua-driver` executable's absolute path. The CLI adds one server to personal `mcp.json`; preserve unrelated servers. Run `/reload`, then try `/skill:computer-use Open Calculator, compute 6 × 7, and verify 42 from a fresh window snapshot.`

The local server controls the real host desktop, not a VM. Screenshots and extracted app text can reach Pi's model provider. The skill recommends narrow captures, live-schema discovery, sequential actions, outcome verification, and explicit authorization for consequential steps; it is not an enforced sandbox or permission gate. For unattended work, use an isolated desktop or a reviewed bounded Driver capability manifest.

### Technical diagrams with Archify

The complete [Archify v3.0.1](https://github.com/tt-a1i/archify/releases/tag/v3.0.1) runtime is bundled under `skills/archify/`; no npm install or separate skill-manager install is needed. It requires Node.js >=18 and Chrome/Chromium for its full automated diagram browser gate. See [provenance and update instructions](skills/archify/PROVENANCE.md).

`visual-explainer` routes standalone technical diagrams to Archify while retaining reports, comparisons, dashboards, and small embedded Mermaid diagrams. `research` and `design-council` can optionally hand off grounded findings or explicitly labeled proposals. Interview response collection, task ownership, and review judgment are unchanged.

Ask, for example: “Use Archify to diagram the cache-miss request path in this repository.” Candidates, HTML, receipts and exports stay inside the owning task's canonical session/Work/Task directory. Repository citations are verified against a pinned committed revision, not uncommitted worktree bytes. Automated checks and actual visual inspection are reported separately.

Archify may check its upstream update manifest and cache a reminder; it does not automatically install updates. Review and update the pinned bundle through this repository instead. Bundled brand marks retain separate license and trademark terms; see the [third-party notices](skills/archify/THIRD_PARTY_NOTICES.md).

### Session coordination

The work-owning skills share one concise coordination rule when the corresponding extensions are loaded:

- **Work** is the overall outcome and is managed with `WorkCreate`, `WorkList`, `WorkUpdate`, and `WorkDelete` from `pi-tasks`.
- **Todo** is a concrete step belonging to a work and is managed with `TodoCreate`, `TodoList`, `TodoUpdate`, and `TodoDelete`.
- **Monitor** runs one long-lived background command through `MonitorCreate`, `MonitorList`, `MonitorUpdate`, and `MonitorStop` from `pi-loop-monitor`.
- **Loop** schedules a future, recurring, event-driven, or idle continuation through `LoopCreate`, `LoopList`, `LoopUpdate`, and `LoopDelete`.

Works and todos stay current as normal work progresses. Monitors are used only for background commands, and loops only when a later or repeated wake is needed. None of these records are changed during `/ask` or `/btw`.

When a skill needs retained notes, screenshots, reports or HTML, it reuses the current owner's canonical task directory from `implement`: `var/<sessionId>/<workId>/<taskId>/` for a root task, or `<exactParentTaskDir>/<childSessionId>/<childWorkId>/<childTaskId>/` for delegated work, recursively. Standalone work establishes real tracking first. Generators receive an explicit `--dir <taskDir>` rather than deriving an output root from feature names or interview slugs. The parent retains aggregate DAGs/contracts and links each worker's original evidence at its actual returned path. Optional subfolders such as `screenshots/`, `questions/` and `diagrams/` stay inside their owner's task directory. Historical feature folders remain untouched; there is no implicit migration. Communication-only skills do not create artifacts merely for uniformity. Tool-managed disposable profiles and package caches are not retained task evidence.

### First Mate coordinator mode

`firstmate` keeps the main conversation in a coordinator role: conversation, decisions, quick inspection and final reporting stay local, while project edits, substantial investigation, builds and verification are delegated through the existing `implement`, `herdr`, and pi-tasks workflow. Saying "implement this" does not leave the role. It is behavioral guidance, not a sandbox, permission gate or elapsed-time classifier, and it blocks no tools.

The companion extension is not installed by `scripts/install.sh`, which installs skills only. Register it once in personal settings and keep the repository checkout available, because the extension reads its policy from `skills/firstmate/SKILL.md` through a module-relative path:

```json
{
  "extensions": ["/absolute/path/to/pi-herdr-skills/extensions/firstmate/index.ts"],
  "pi-firstmate": { "enabled": false }
}
```

`pi-firstmate.enabled` defaults to `false` when omitted. A trusted project `.pi/settings.json` can override it. `/firstmate on` and `/firstmate off` set a session-only override, `/firstmate default` clears it, and `/firstmate status` reports the effective state, configured default and worker suppression. The override is stored in the session and is not inherited by forked or new sessions.

Worker sessions started by pi-herdr `AgentCreate` are recognized from their verified Core `pi.task` and `pi.session` labels, so coordinator guidance stays off there even when the default is on. `/firstmate on` in a worker explains the suppression instead of restricting it. A malformed settings section is reported and treated as off rather than silently enabling the mode. Reload or restart Pi after registering the extension, then run `/firstmate on`. See [`config/firstmate.example.json`](config/firstmate.example.json) for the settings section.

## Permission gates

This repository no longer installs or requires tool-permission gates. If you installed the previously required extension, remove it globally and reload or restart every running Pi session, including Herdr agents:

```bash
pi remove npm:@gotgenes/pi-permission-system
```

Old policy files and review logs are not needed by the skills. Removing the extension also removes its destructive-command and sensitive-path protection; it does not change Pi's built-in project trust or unrelated skill safety rules.

### Browser workflow prerequisite

`browser-use` and browser-based visual work require the current Browser Use CLI.

```bash
uv tool install --python 3.12 --upgrade --force browser-use
browser-use --doctor
browser-use skill show
```

Browser actions use Python through standard input with pre-imported helpers. The older command-mode interface (`--session`, `open`, `state`, `click`, `input`, `eval`, and `record start/stop`) is not supported by the bundled skill.

## Herdr Core setup

Delegated workflows use **herdr-core (`hc`)** for interactive Pi processes and **herdr-app** for dedicated visible worker tabs. The old `herdr` TUI CLI and its socket integration are not used.

1. Install the app/Core using the official [app download](https://herdr.dev/download/) and [Core guide](https://herdr.dev/core/). Inspect installer scripts before running them. The app installs Core if needed; do not install the old Homebrew `herdr` formula for these workflows.
2. Open the Herdr app, open a project terminal, and run a current Pi version with native OSC 7501 status support (verified with Pi 1.4.0). No legacy `herdr-agent-state.ts` integration is needed for Core status.
3. Verify with `hc --version`, `herdr-app --version`, and `hc get "$HC_TERMINAL_ID" --json`. Require a real live Core terminal and its app mapping, not a fabricated variable. Missing HERDR_ENV is normal in Core and must not block parallel grill-me branches.
4. Install pi-herdr, compatible pi-tasks and pi-loop-monitor together, synchronize the managed skills, then run /reload or restart Pi so tool schemas use terminalId/hcTerminalId rather than legacy pane IDs. The `herdr` skill is bundled with pi-herdr rather than managed by this repository.

AgentCreate starts interactive Pi through hc with explicit model settings, verifies native input readiness and **one dedicated visible tab per worker**, named exactly with the parent Task ID. It registers continuous monitoring but sends no assignment. Confirm MonitorList's Core subscription ready receipt before AgentSend. hc --bg does not itself prove a visible tab exists; the wrapper checks the real app mapping. Use hc for messages/status/output/cleanup and herdr-app for focus. No hidden-worker substitute or TUI fallback.

The app closing leaves Core programs running. Core children normally end with their parent program. Do not stop a user's existing TUI server to migrate: finish or explicitly retire its sessions first, then uninstall the old integration/binary without deleting session history.

## Extensions in the source setup

The following package versions were installed globally when this repository was created. They are documented here for reproducibility, but their source code is **not** copied into this repository.

| Package | Snapshot version | What it adds | Source |
| --- | ---: | --- | --- |
| `pi-web-access` | `0.25.0` | Web search, URL fetching, repositories, PDFs, and video tools | [GitHub](https://github.com/nicobailon/pi-web-access) |
| `pi-btw` | `0.4.1` | Parallel `/btw` side conversations | [GitHub](https://github.com/dbachelder/pi-btw) |
| `@narumitw/pi-usage` | `0.52.3` | Account-usage display | [GitHub](https://github.com/narumiruna/pi-extensions/tree/main/packages/pi-usage) |
| `@abhishek944/pi-image-gen` | `0.1.1` | Image generation tools and an image-generation skill | [GitHub](https://github.com/abhishek944/pi-image-gen) |
| `@narumitw/pi-goal` | `0.54.3` | Autonomous single-goal workflow | [GitHub](https://github.com/narumiruna/pi-extensions/tree/main/packages/pi-goal) |
| `@abhishek944/pi-ask` | `0.1.0` | Limited-tool, one-shot `/ask` command | [GitHub](https://github.com/abhishek944/pi-ask) |
| Pi native OSC 7501 status | current Pi | Reports Pi lifecycle directly to Core; replaces the old TUI-only managed integration for this setup | [Pi terminal setup](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/terminal-setup.md) |

Install the same package versions:

```bash
pi install npm:pi-web-access@0.25.0
pi install npm:pi-btw@0.4.1
pi install npm:@narumitw/pi-usage@0.52.3
pi install npm:@abhishek944/pi-image-gen@0.1.1
pi install npm:@narumitw/pi-goal@0.54.3
pi install npm:@abhishek944/pi-ask@0.1.0
```

Pinned versions recreate the recorded setup. Remove `@<version>` if you intentionally want the latest release. Manage installed packages with `pi list`, `pi config`, `pi update --extensions`, and `pi remove`; see [Pi packages](https://pi.dev/docs/latest/packages).

Package-provided skills, such as the image-generation skill, remain owned and updated by their packages. They are not duplicated under this repository's `skills/` directory, which avoids name collisions and stale copies.

## Maintenance and safety

- Run `npm run check` before installing, committing, or publishing.
- Keep credentials in environment variables or provider login stores, never in skills or examples.
- Do not commit Pi settings, sessions, Herdr configuration, generated `var/` evidence, package caches, or `node_modules/`.
- Review upstream extension release notes before updating pinned versions.
- Keep skill instructions concise and easy to audit.
- Preserve file modes when copying or packaging skills.
- Third-party names and links are informational; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Repository layout

```text
skills/                 Shared Agent Skills directories (Pi, Codex, OpenCode)
skills-manifest.json    Exact skill file checksums and executable modes
scripts/install.sh      Conflict-safe global installer and uninstaller
scripts/check-repo.sh   Repository/global skill equality check
third_party/licenses/   Required upstream license texts
package.json            Repository metadata and check command
```

## License

The repository's original packaging and documentation are available under the [MIT License](LICENSE). Redistributed material keeps its upstream terms and required notices in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`third_party/licenses/`](third_party/licenses/).
