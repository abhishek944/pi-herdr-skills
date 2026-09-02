# pi-herdr-skills

A portable snapshot of 14 global [Pi](https://pi.dev/) skills for planning, implementation, review, browser work, visual explanations, and [Herdr](https://herdr.dev/)-hosted Pi agents.

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

The installer copies all 14 skills into Pi's global `~/.pi/agent/skills/` directory. It refuses to overwrite a different skill with the same name. If you intentionally replace conflicts, `./scripts/install.sh --force` backs up the existing directories under `~/.pi/agent/skills-backups/` first.

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
| `grill-me` | Challenges a plan through a browser-based decision interview. |
| `herdr` | Controls Herdr panes and Herdr-hosted Pi agents when a workflow authorizes it. |
| `herdr-orchestrator` | Monitors work across Herdr workspaces, safely recovers narrow transient failures, escalates decisions, and suggests grounded follow-ups. |
| `implement` | Coordinates implementation with task state, Herdr delegation, checks, and review. |
| `model-routing-policy` | Selects and verifies provider, model, and thinking settings for delegated Pi agents. |
| `plainspoken-responses` | Keeps user-facing replies clear, friendly, and easy to follow. |
| `read-flows` | Finds and reads repository flow documentation before relevant changes. |
| `ui-ux-grill-me` | Captures an interface and records visual UX choices in a browser. |
| `visual-explainer` | Produces self-contained HTML explanations, diagrams, comparisons, and data views. |

Some skills depend on other skills in this repository. Install the complete set rather than copying only `implement`, `agent-review`, or `design-council`.

### Browser workflow prerequisite

`browser-use` and the automated capture steps in `ui-ux-grill-me` require the Browser Use CLI. Human question and comparison pages in `grill-me` and `ui-ux-grill-me` open through the operating system's visible default browser instead; on macOS they use `open` and never Browser Use. This snapshot uses the command interface from [`browser-use` 0.12.9](https://github.com/browser-use/browser-use/blob/0.12.9/browser_use/skill_cli/README.md):

```bash
uv tool install 'browser-use==0.12.9'
browser-use doctor
```

Use that pinned version unless you also update and recheck the bundled browser skill against a newer CLI.

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

The agent workflows never silently weaken their requirements. When automatic routing hits a model-specific quota or availability failure before any useful work, they try another eligible catalog model with the same task, quality, input, thinking, and review requirements. Explicit user model choices, Herdr setup failures, uncertain partial work, exhausted candidates, and launch-verification failures still stop safely. Read the [Herdr agent guide](https://herdr.dev/agent-guide.md) for concepts and controls.

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
- Check executable helper scripts as carefully as extensions.
- Preserve executable file modes when copying or packaging skills.
- Third-party names and links are informational; see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Repository layout

```text
skills/                 Pi skill directories and their supporting files
skills-manifest.json    Exact skill file checksums and executable modes
scripts/install.sh      Conflict-safe global installer and uninstaller
scripts/check-repo.sh   Structure, portability, and sensitive-data checks
third_party/licenses/   Required upstream license texts
package.json            Repository metadata and check command
```

## License

The repository's original packaging and documentation are available under the [MIT License](LICENSE). Redistributed material keeps its upstream terms and required notices in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and [`third_party/licenses/`](third_party/licenses/).
