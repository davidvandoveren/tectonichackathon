# Security & compliance

Security is 10% of the score, measured with the **Aikido AI Code Audit** (before/after
screenshots). This page is the map: what Aikido looks for, what we do about it, where it lives in
the code and which test proves it. Keep it true when you change the code.

## How Aikido judges a repo

- **Code Audit (AI, agentic):** reads the source like a pentester and chains context across files.
  It hunts for access-control flaws (IDOR/BOLA, privilege escalation), injection (SQL, command,
  SSTI), business-logic flaws (workflow bypasses, payment shortcuts), agentic-AI risks (prompt
  injection, excessive agency, insecure tool use; OWASP Top 10 for Agentic Applications) and
  algorithmic-complexity attacks (ReDoS). Each finding comes with a root cause and evidence in code.
- **Classic scanners:** SAST, open-source dependencies (SCA, CVEs and licences), secrets in git,
  IaC/Dockerfile/CI misconfiguration. Findings are ranked by severity and reachability.

## Controls

| Aikido looks for | What we do | Where | Proven by |
|---|---|---|---|
| IDOR / BOLA | Every query takes the logged-in user's id; someone else's id is the same 404 as a missing one | `domain/bank.py`, `skills/service.py`, `routers/subscriptions.py` | `test_banking.py::test_idor_*`, `test_skills_core.py::test_another_customer_*` |
| Broken authentication | Server-side sessions (hash only), rotated on login, revoked on logout, `__Host-` HttpOnly SameSite=Strict cookie; scrypt; timing-equal unknown users | `security/sessions.py`, `routers/auth.py` | `test_auth.py` |
| Brute force | Login limiter per user **and** per real client IP; the IP comes from the proxy hop, never from a client-supplied `X-Forwarded-For` | `security/client_ip.py`, `TRUSTED_PROXY_HOPS` | `test_security_hardening.py::test_login_limiter_cannot_be_dodged_*` |
| Privilege escalation | Admin endpoints answer 404 unless `ADMIN_USERNAMES` lists you | `dependencies.py::get_admin_user` | `test_kate_feed.py` |
| CSRF | SameSite=Strict + JSON-only + Origin check on every state change | `security/headers.py` | `test_banking.py::test_csrf_guard_*` |
| XSS / clickjacking / open redirect | React escaping, strict CSP (no inline script), `frame-ancestors 'none'`; internal links only (no `//`, `\`, control chars) | `security/headers.py`, `frontend/src/lib/cta.ts` | `test_security_headers_present`, `cta.test.ts` |
| Business logic: payments | Amount > 0, ≤ € 10 000, 2 decimals, sufficient funds, no same account, no credit-card source; re-checked **in the bank itself** so no internal caller can skip it | `schemas.py`, `domain/bank.py` | `test_banking.py::test_transfer_business_rules`, `test_bank_rejects_invalid_amounts_*` |
| Excessive agency (AI) | Kate only *proposes*; paying a third party is capped at "prepare" (human confirms); automatic actions need a mandate with hard ceilings (€ 500 / € 1 000 per month); regulated topics go to a human | `skills/base.py`, `skills/consent.py`, `kate/assistant.py` | `test_skills_core.py` |
| Prompt injection | Customer data is fenced as data in the prompt, free text is cleaned, model output is schema-validated and anything else is dropped | `kate/context.py`, `kate/assistant.py` | `test_kate.py::test_prompt_injection_*`, `test_invalid_model_action_is_dropped` |
| ReDoS | Chat text is whitespace-normalised before the one non-trivial regex (was 0.7 s per request, now < 1 ms) | `kate/llm.py` | `test_mock_chat_is_linear_on_hostile_whitespace` |
| Resource exhaustion | Request body cap (64 KiB; 1 MiB for chat, 3 MiB for speech); caps on sessions per user, open/kept proposals, activity log, goals, standing orders, dismissible moments; Kate rate limit | `security/body_limit.py`, `security/sessions.py`, `skills/service.py` | `test_security_hardening.py` |
| Information leakage | No API docs in production, validation errors never echo input, no server header, `no-store` on the API | `main.py` | `test_auth.py::test_validation_errors_do_not_echo_input` |
| Security logging | Failed and blocked logins logged, never passwords; user input logged with `%r` (no log injection) | `routers/auth.py` | `test_failed_login_is_logged_*` |
| Secrets | Only via env / Secret Manager; `.env` git-ignored; no keys in the frontend | `.gitignore`, `deploy/cloudrun.sh` | – |
| Dependencies | Pinned backend versions, lockfile for the frontend, `pip-audit` + `npm audit` in CI, Dependabot | `requirements.txt`, `.github/` | CI |
| IaC / container | Non-root, HEALTHCHECK, read-only FS + dropped capabilities (compose); Cloud Run runs as its own service account with only secret access; CI with read-only token and `persist-credentials: false` | `Dockerfile`, `compose.yaml`, `deploy/cloudrun.sh`, `.github/workflows/ci.yml` | – |
| Disclosure | `SECURITY.md` and `/.well-known/security.txt` (RFC 9116) | `main.py` | `test_security_txt_and_noindex` |

## Legal / privacy

| Rule | How we meet it |
|---|---|
| GDPR art. 5, 25: minimisation, privacy by design | Synthetic data only, in memory; Kate gets summaries without IBANs; consent per signal domain is applied *before* anything is computed |
| GDPR art. 9: sensitive data | Health, religion, politics, trade union and dating spend is neutralised before the AI sees it and hidden in the subscription manager (engine fix for the Moments feed: #35) |
| GDPR art. 22: automated decisions | No credit, investment or insurance decision by Kate; always a human advisor |
| GDPR art. 13: transparency | Public `/privacy` page (linked on the login screen and in Profiel) |
| ePrivacy art. 5(3): cookies | Only a strictly necessary session cookie and a local view preference, so no banner |
| EU AI Act art. 50 | Kate says she is an AI (UI badge and first answer, enforced server-side) |
| MiFID II / consumer credit | Kate gives no product advice; regulated actions are hand-offs |
| No impersonation | "Prototype, not an official KBC app" on the login screen and `/privacy`; `noindex` so it never shows up in search |

## Known limitations (on purpose, for a PoC)

- One shared demo password (or passwordless demo mode), no MFA/itsme, no PSD2 strong customer
  authentication.
- In-memory state and per-instance rate limits (Cloud Run runs with one instance).
- GitHub Actions and base images are pinned to tags, not digests.

## Submission checklist

1. Run the **Aikido baseline scan on `main` before merging the security PR** and screenshot it.
2. Merge, run the scan again, screenshot the "after".
3. Fix or triage every remaining finding; note accepted risks here.
