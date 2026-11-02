# Third-party notices

This repository is a curated skills snapshot. The repository's original packaging and documentation use the root [MIT License](LICENSE). Redistributed material retains the following upstream terms.

## Archify

- Covered files: `skills/archify/`
- Upstream: [tt-a1i/archify](https://github.com/tt-a1i/archify), v3.0.1 at `2ab3cae7ac2c2a55d7386ca789d03c4fcd31816c`
- License: MIT for Archify code and content
- Copyright: Copyright (c) 2026 tt-a1i (Archify); Copyright (c) 2025 Cocoon AI
- Required text: [`skills/archify/LICENSE`](skills/archify/LICENSE)
- Complete release runtime retained without modifications; skill instructions adapted for this repository. See [`PROVENANCE.md`](skills/archify/PROVENANCE.md) for the archive checksum and local adaptations.
- Bundled brand marks retain their own copyright, license, and trademark terms; see [`skills/archify/THIRD_PARTY_NOTICES.md`](skills/archify/THIRD_PARTY_NOTICES.md). JetBrains Mono uses the [bundled SIL Open Font License](skills/archify/assets/JetBrainsMono-OFL.txt).

## awesome-logging-standards

- Covered files: `skills/awesome-logging-standards/`
- Upstream: [khasky/awesome-agent-skills](https://github.com/khasky/awesome-agent-skills/tree/58ea4e8915de64907d04cc909a1b8c6e5cf0fcb7/skills/awesome-logging-standards) at `58ea4e8915de64907d04cc909a1b8c6e5cf0fcb7`
- License: MIT
- Copyright: Copyright (c) 2026 Khasky
- Required text: [`skills/awesome-logging-standards/LICENSE`](skills/awesome-logging-standards/LICENSE)
- Adaptations: Pi workflow integration, redaction instead of sensitive-data sampling, authorized local verification, framework-aware request completion, and TypeScript/Effect error and context guidance. See [`PROVENANCE.md`](skills/awesome-logging-standards/PROVENANCE.md).

## browser-use

- Covered files: `skills/browser-use/`
- Upstream: [browser-use/browser-use](https://github.com/browser-use/browser-use)
- License: MIT
- Copyright: Copyright (c) 2024 Gregor Zunic
- Required text: [`third_party/licenses/browser-use-MIT.txt`](third_party/licenses/browser-use-MIT.txt)

## Caveman

- Covered files: `skills/caveman/` (skill only; no CLI, proxy, hooks, or telemetry)
- Upstream: [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) at `f5d729488caa8f6a5b6c8086fe2cccd3e8a63f91`
- License: Apache License 2.0 (skill redistributed without local modifications)
- Copyright: Copyright 2026 Julius Brussee
- Required text: [`third_party/licenses/caveman-Apache-2.0.txt`](third_party/licenses/caveman-Apache-2.0.txt); earlier MIT contributions are retained under [`third_party/licenses/caveman-MIT.txt`](third_party/licenses/caveman-MIT.txt).

## Herdr skill migration

The Herdr-derived skill is now distributed by [pi-herdr](https://github.com/abhishek944/pi-herdr), not this repository. That package retains the Apache-2.0 license text and original-import provenance alongside its locally adapted skill.

## codebase-design

- Covered files: `skills/codebase-design/`
- Upstream: [mattpocock/skills](https://github.com/mattpocock/skills/tree/d80fa0f4ebe0c5714af0adf8670336065233ecc6/skills/engineering/codebase-design) at `d80fa0f4ebe0c5714af0adf8670336065233ecc6`
- License: MIT
- Copyright: Copyright (c) 2026 Matt Pocock
- Required text: [`skills/codebase-design/LICENSE`](skills/codebase-design/LICENSE)
- Adaptations: condensed the skill and its deepening/design-it-twice references into one design reference; retained repository/library terminology, made independent agents proportionate, preserved unit-test permissions and workflow ownership, and added version-aware TypeScript/Effect contracts. Integration remains in the existing design, implementation, and review workflows.

## retro

- Covered files: `skills/retro/SKILL.md`
- Upstream: [mattpocock/skills](https://github.com/mattpocock/skills/tree/d81f3a183412e71a5b1e84ca21bc1a35eea03a60/skills/engineering/retro) at `d81f3a183412e71a5b1e84ca21bc1a35eea03a60`
- License: MIT
- Copyright: Copyright (c) 2026 Matt Pocock
- Required text: [`third_party/licenses/retro-MIT.txt`](third_party/licenses/retro-MIT.txt)
- Adaptations: replaced references to the unavailable `Skill` tool and `writing-for-agents` skill with Pi's global `talk-human` skill and local concise-skill guidance; omitted OpenAI-only `agents/openai.yaml` UI metadata. The rest of the upstream skill is retained.

## security-audit

- Covered files: `skills/security-audit/`
- Upstream: [cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill) at `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`
- License: MIT
- Copyright: Copyright (c) 2025-2026 Cloudflare, Inc.
- Required text: [`skills/security-audit/LICENSE`](skills/security-audit/LICENSE)
- Adaptations: Pi coordination, delegation, unit-test permissions, and explicit full-audit path compatibility guidance. Upstream unit tests are omitted; companion documents, schema, and validators are unchanged. See [`PROVENANCE.md`](skills/security-audit/PROVENANCE.md).

## visual-explainer

- Covered files: `skills/visual-explainer/`
- Upstream: [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer)
- License: MIT
- Copyright: Copyright (c) 2025 Nico Bailon
- Required text: [`third_party/licenses/visual-explainer-MIT.txt`](third_party/licenses/visual-explainer-MIT.txt)

## Linked but not redistributed

The extension packages listed in the README are not copied into this repository. Each remains subject to the license in its linked source repository or npm package.

Some templates load browser assets such as Google Fonts, Mermaid, ELK, Chart.js, or Anime.js at runtime. Those assets are fetched from their named upstream services and are not stored in this repository. Their names, URLs, copyrights, and license terms remain those of their upstream projects.

Product and project names belong to their respective owners.
