# Contributing

## Branches
`main` is protected. Work on short-lived branches named `type/short-description`:
`feature/…`, `fix/…`, `docs/…`, `chore/…`.

## Pull requests
- All changes go through a PR (direct pushes to `main` are blocked). No approval is required: every collaborator can merge their own PR once CI is green. A quick review from a teammate is still welcome for bigger changes.
- Fill in the PR template. Link the issue if there is one.
- Keep PRs focused and small; draft PRs are welcome for early feedback.
- Resolve all review conversations before merging. Prefer **squash merge** for a clean history.
- Don't push to a branch someone else owns without asking.

## Commits
Short imperative subject line (max ~70 chars), e.g. `Add synthetic customer generator`. Explain *why* in the body if it's not obvious.

## Code quality & security
- Validate input, check authorization on every data access (Aikido audits for IDOR, auth and business-logic flaws).
- No secrets in the repo; use environment variables (`.env` is git-ignored). If you leak a secret, rotate it immediately and tell the team.
- Run the Aikido AI Code Audit on the repo before final submission and fix findings.

## Hackathon rules reminder
Final submission is final – after that, no code changes. Keep the repo public until judging is complete.
