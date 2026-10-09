# pi-herdr-skills

A portable snapshot of 18 global [Pi](https://pi.dev/) skills for planning, implementation, review, browser work, visual explanations, and [Herdr](https://herdr.dev/)-hosted Pi agents.

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

The installer copies all 18 skills into the shared global `~/.agents/skills/` directory (discovered by Pi, Codex, and OpenCode). It does not require or install a permission extension or policy. It refuses to overwrite a different managed skill. If you intentionally replace conflicts, `./scripts/install.sh --force` backs up the existing files under `~/.pi/agent/skills-backups/` first.

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
| `agent-review` | Runs independent correctness, architecture, and regression reviews before shipping. |
| `archify` | Renders and validates interactive architecture, workflow, sequence, data-flow, and state diagrams. |
| `browser-use` | Automates browser navigation, forms, screenshots, testing, and extraction. |
| `commit-and-merge` | Commits real changes and merges into the default branch when explicitly requested. |
| `design-council` | Compares architecture, API, workflow, and product-design options without editing. |
| `research` | Investigates and debugs a repository without applying a fix. |
| `next-feature` | Autonomously recommends what to build next from real user problems, web evidence, product fit, and code-grounded sizing. |
| `grill-me` | Challenges a plan in DAG levels with parallel browser branch owners and recorded follow-ups. |
| `herdr` | Controls Herdr panes and Herdr-hosted Pi agents when a workflow authorizes it. |
| `model-routing-policy` | Defines shared subagent model, thinking, and Fast defaults in one editable file. |
| `implement` | Coordinates implementation with a short written plan, checks, and proportionate review. |
| `no-unit-tests` | Prevents unit-test creation or execution unless the user explicitly requests it. |
| `talk-human` | Combines clear, friendly replies with Caveman's lite brevity. |
| `caveman` | Optional standalone concise response styles; bundled skill-only under Apache-2.0. |
| `read-flows` | Finds and reads repository flow documentation before relevant changes. |
| `retro` | Reviews a coding session for ways to improve the agent's working environment; invoke explicitly with `/skill:retro`. |
| `ui-ux-grill-me` | Captures an interface and resolves independent UX branches in parallel browser interviews. |
| `visual-explainer` | Produces self-contained HTML explanations, diagrams, comparisons, and data views. |

Some skills depend on other skills in this repository. Install the complete set rather than copying only `implement`, `agent-review`, or `design-council`.

Edit `skills/model-routing-policy/SKILL.md` to change subagent model, thinking, and Fast defaults. `implement`, `agent-review`, `herdr`, `grill-me`, and `ui-ux-grill-me` read that shared policy before launching agents. Explicit user choices override its defaults; the parent agent's model is unchanged. Reinstall after editing so the global copy stays current.

### Technical diagrams with Archify

The complete [Archify v3.0.1](https://github.com/tt-a1i/archify/releases/tag/v3.0.1) runtime is bundled under `skills/archify/`; no npm install or separate skill-manager install is needed. It requires Node.js >=18 and Chrome/Chromium for its full automated diagram browser gate. See [provenance and update instructions](skills/archify/PROVENANCE.md).

`visual-explainer` routes standalone technical diagrams to Archify while retaining reports, comparisons, dashboards, and small embedded Mermaid diagrams. `research` and `design-council` can optionally hand off grounded findings or explicitly labeled proposals. Interview response collection, task ownership, and review judgment are unchanged.

Ask, for example: “Use Archify to diagram the cache-miss request path in this repository.” Candidates, HTML, receipts, and exports stay under `var/<feature-name>/archify-details/`. Repository citations are verified against a pinned committed revision, not uncommitted worktree bytes. Automated checks and actual visual inspection are reported separately.

Archify may check its upstream update manifest and cache a reminder; it does not automatically install updates. Review and update the pinned bundle through this repository instead. Bundled brand marks retain separate license and trademark terms; see the [third-party notices](skills/archify/THIRD_PARTY_NOTICES.md).

### Session coordination

The work-owning skills share one concise coordination rule when the corresponding extensions are loaded:

- **Work** is the overall outcome and is managed with `WorkCreate`, `WorkList`, `WorkUpdate`, and `WorkDelete` from `pi-tasks`.
- **Todo** is a concrete step belonging to a work and is managed with `TodoCreate`, `TodoList`, `TodoUpdate`, and `TodoDelete`.
- **Monitor** runs one long-lived background command through `MonitorCreate`, `MonitorList`, `MonitorUpdate`, and `MonitorStop` from `pi-loop-monitor`.
- **Loop** schedules a future, recurring, event-driven, or idle continuation through `LoopCreate`, `LoopList`, `LoopUpdate`, and `LoopDelete`.

Works and todos stay current as normal work progresses. Monitors are used only for background commands, and loops only when a later or repeated wake is needed. None of these records are changed during `/ask` or `/btw`.

When a skill needs to retain notes, screenshots, reports, or HTML, it writes to `var/<feature-name>/<skill-name>-details/` in the working repository.

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

## Herdr setup

The implementation and review workflows require Herdr-hosted Pi agents.

1. Install Herdr using an option from the official [installation guide](https://herdr.dev/docs/install/). Prefer a package manager you already trust:

   ```bash
   brew install herdr
   # or
   mise use -g herdr
   ```

   For Herdr's direct Linux/macOS installer, download and inspect it before running it:

   ```bash
   curl -fsSLo herdr-install.sh https://herdr.dev/install.sh
   less herdr-install.sh
   sh herdr-install.sh
   rm herdr-install.sh
   ```

2. Install Herdr's managed Pi integration:

   ```bash
   herdr integration install pi
   herdr integration status
   ```

   This writes Herdr's lifecycle extension to Pi's global extension directory. Do not copy or maintain that generated extension by hand; rerun the integration command after Herdr upgrades. See [Herdr integrations](https://herdr.dev/docs/integrations/).

3. Start Herdr in a project and launch Pi inside a Herdr pane:

   ```bash
   cd /path/to/your-project
   herdr
   # In a Herdr pane:
   pi
   ```

4. Confirm the environment when troubleshooting:

   ```bash
   herdr --version
   herdr integration status
   ```

The skills use Herdr directly. They create one dedicated tab with one root pane per agent, name the pane, wait for a clean interactive shell, pass explicit Pi model settings, collect the result, and close only resources they created. Read the [Herdr agent guide](https://herdr.dev/agent-guide.md) for concepts and controls.

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
| Herdr Pi integration | managed by Herdr | Reports Pi lifecycle and session state to Herdr | [Herdr integrations](https://herdr.dev/docs/integrations/) |

Install the same package versions:

```bash
pi install npm:pi-web-access@0.25.0
pi install npm:pi-btw@0.4.1
pi install npm:@narumitw/pi-usage@0.52.3
pi install npm:@abhishek944/pi-image-gen@0.1.1
pi install npm:@narumitw/pi-goal@0.54.3
pi install npm:@abhishek944/pi-ask@0.1.0
herdr integration install pi
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
