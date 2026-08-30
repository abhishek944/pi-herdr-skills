# Security

Pi extensions run as code with the user's permissions. Skills can instruct an agent to run commands and may include executable helper scripts.

Before installing:

1. Review the skill instructions and executable files.
2. Review every separately installed extension at its linked source.
3. Use project trust and normal operating-system isolation for untrusted repositories.
4. Keep API keys, login stores, Pi settings, session files, and Herdr configuration out of this repository.

If you find a credential or personal detail in the repository, remove it from the working tree and Git history before publishing. Rotate any exposed credential even after history is cleaned.

Report security concerns through the repository's private GitHub security-advisory feature rather than a public issue.
