# pi-herdr-skills

A portable snapshot of 14 global [Pi](https://pi.dev/) skills and a permission-gate extension for planning, implementation, review, browser work, visual explanations, and [Herdr](https://herdr.dev/)-hosted Pi agents.

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

The installer copies all 14 skills into Pi's global `~/.pi/agent/skills/` directory and `extensions/permission-gate.ts` into `~/.pi/agent/extensions/`. It refuses to overwrite a different managed skill or extension. If you intentionally replace conflicts, `./scripts/install.sh --force` backs up the existing files under `~/.pi/agent/skills-backups/` first.

A global copy is required for these workflows because `model-routing-policy` deliberately accepts only Pi's trusted global model catalog. Do not install this repository as a Git-backed Pi package; that package location would make the implementation and review workflows stop at their model-routing safety check.

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
rm -rf -- "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}/skills/herdr-orchestrator"
```

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
| `browser-use` | Automates browser navigation, forms, screenshots, testing, and extraction. |
| `commit-and-merge` | Commits real changes and merges into the default branch when explicitly requested. |
| `design-council` | Compares architecture, API, workflow, and product-design options without editing. |
| `discuss` | Investigates and debugs a repository without applying a fix. |
| `grill-me` | Challenges a plan one decision at a time and records the answers. |
| `herdr` | Controls Herdr panes and Herdr-hosted Pi agents when a workflow authorizes it. |
| `implement` | Coordinates implementation with a short written plan, checks, and proportionate review. |
| `model-routing-policy` | Selects explicit provider, model, and thinking settings for delegated Pi agents. |
| `no-unit-tests` | Prevents unit-test creation or execution unless the user explicitly requests it. |
| `plainspoken-responses` | Keeps user-facing replies clear, friendly, and easy to follow. |
| `read-flows` | Finds and reads repository flow documentation before relevant changes. |
| `ui-ux-grill-me` | Captures an interface and records visual UX choices in a browser. |
| `visual-explainer` | Produces self-contained HTML explanations, diagrams, comparisons, and data views. |

Some skills depend on other skills in this repository. Install the complete set rather than copying only `implement`, `agent-review`, or `design-council`.

### Session coordination

The work-owning skills share one concise coordination rule when the corresponding extensions are loaded:

- **Work** is the overall outcome and is managed with `WorkCreate`, `WorkList`, `WorkUpdate`, and `WorkDelete` from `pi-tasks`.
- **Todo** is a concrete step belonging to a work and is managed with `TodoCreate`, `TodoList`, `TodoUpdate`, and `TodoDelete`.
- **Monitor** runs one long-lived background command through `MonitorCreate`, `MonitorList`, `MonitorUpdate`, and `MonitorStop` from `pi-loop-monitor`.
- **Loop** schedules a future, recurring, event-driven, or idle continuation through `LoopCreate`, `LoopList`, `LoopUpdate`, and `LoopDelete`.

Works and todos stay current as normal work progresses. Monitors are used only for background commands, and loops only when a later or repeated wake is needed. None of these records are changed during `/ask` or `/btw`.

When a skill needs to retain notes, screenshots, reports, or HTML, it writes to `var/<feature-name>/<skill-name>-details/` in the working repository.

## Included extension

`extensions/permission-gate.ts` blocks catastrophic or ambiguous shell operations and asks for explicit confirmation before other destructive commands. In Pi's TUI, it emits balanced `herdr:blocked` open/close events around each confirmation; the Herdr integration counts overlapping waits so connected interfaces remain in their permission-waiting state until every dialog closes. Print and JSON modes reject confirmation-covered commands without prompting. RPC mode can request confirmation, but its wait is not reported as a Herdr pet state. An exact recursive-deletion target outside the current project may proceed only after confirmation in an interactive Pi session. Broad targets, parent traversal, filesystem or home roots, protected system roots, and credential-sensitive paths remain blocked.

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

The skills use Herdr directly. They keep at most four panes per tab, name every work pane, wait for a clean interactive shell, pass explicit Pi model settings, collect the result, and close only resources they created. Read the [Herdr agent guide](https://herdr.dev/agent-guide.md) for concepts and controls.

### Subagent model policy

Routine non-review agents use **GPT-5.6 Sol or Terra only**. Sol handles general
work; Terra is preferred for focused edits. Independent review runs automatically
only for substantial features or complicated changes where complexity, risk, breadth,
or uncertainty makes direct inspection insufficient. Straightforward low-risk changes,
including localized UI work across closely related files, skip review when normal checks
and direct inspection are enough. Explicitly requested simple reviews use **GPT-5.6 Sol**. **GPT-6 Astra at high thinking** is reserved for complicated
reviews. Outside review, Astra requires an evidence-based exceptional-debugging
exploration in the shared resolver. Production impact, timeouts, simple review, or
unavailable Sol/Terra models do not unlock Astra. Other catalog entries are retained
only for caller/contributor verification. No eligible permitted model means a clear blocker, not a wider
fallback. See [model-routing-policy](skills/model-routing-policy/SKILL.md).

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
skills/                 Pi skill directories
extensions/             Pi command-safety extensions
skills-manifest.json    Exact skill file checksums and executable modes
scripts/install.sh      Conflict-safe global installer and uninstaller
scripts/check-repo.sh   Structure, portability, and sensitive-data checks
third_party/licenses/   Required upstream license texts
package.json            Repository metadata and check command
```

## License

The repository's original packaging and documentation are available under the [MIT License](LICENSE). Redistributed material keeps its upstream terms and required notices in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`third_party/licenses/`](third_party/licenses/).
