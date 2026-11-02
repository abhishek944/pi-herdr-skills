# Logging standards provenance

- Upstream: https://github.com/khasky/awesome-agent-skills
- Revision: `58ea4e8915de64907d04cc909a1b8c6e5cf0fcb7`
- Source: `skills/awesome-logging-standards/SKILL.md`
- Author: Khasky
- License: MIT; upstream copyright and permission notice are retained in `LICENSE`.

## Local adaptations

- Integrate with Pi's existing implementation coordination, talk-human, and no-unit-tests skills without expanding authorization.
- Replace sensitive-data sampling advice with omission/redaction before emission; sampling controls volume only.
- Limit failure verification to authorized safe local checks, with user-owned live steps otherwise.
- Use framework completion hooks for accurate request summaries, including streaming and outer error handling.
- Reuse existing TypeScript/Node.js or Effect logging; retain error causes, avoid duplicate error reports, and isolate concurrent request context.

Update from a reviewed upstream revision, reapply these adaptations, update the repository manifest checksums, and synchronize this entire skill directory to `~/.agents/skills/awesome-logging-standards/`.
