# Contributing — plv-labs-website

## Credentials never enter this repository

Credentials live in exactly two places: `~/.hermes/.env` on your machine (local runs) and
the secrets of the service that runs the code (GitHub Actions secrets, Vercel environment
variables, Supabase / Fly / Asaas dashboards). Never in a tracked file, never in a commit
message, never in a test fixture.

What that means in practice:

- `.gitignore` ignores `.env`, `.env.*` (examples stay tracked), `key.properties`, `*.jks`,
  `*.keystore`, `*.p12`, `*.p8`, `*.mobileprovision`, `google-services.json`,
  `GoogleService-Info.plist` and service-account JSON. Keep them ignored. If a build needs
  one of those files, generate it from a CI secret or keep it on your machine.
- CI runs `Secrets Scan` (gitleaks) on every pull request and fails the PR when one of its
  commits contains a credential. Pushes to the default branch are scanned as well. The
  same workflow can be run by hand from the Actions tab to scan the whole history.
- `.gitleaks.toml` records the findings that already exist in this repository's history —
  accepted legacy, kept only so the scans above stay usable. It is not permission: never
  add an entry to hide a new secret.
- Optional local guard: run `git config core.hooksPath .githooks` once per clone to have the
  pre-commit hook check staged changes with the same rules (`brew install gitleaks` first).
  Turn it off with `git config --unset core.hooksPath`.

If a credential does reach a commit: rotate it first, then say which credential and where it
landed. Never rewrite history on your own — that is a founder decision.

<!-- secrets-guard: end -->
