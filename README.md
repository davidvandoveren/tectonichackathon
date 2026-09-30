# Tectonic Hackathon – KBC Challenge

> Tectonic Hackathon, 30 September 2026 · Case partner: **KBC** · Status: 🚧 work in progress

## The challenge

KBC is one of the largest banks in Belgium (banking, investment, insurance) with **2,300,000+ customers**.

> *Imagine a future where KBC perfectly understands what customers need and responds at exactly the right moment.*

First think without constraints: what would the ideal customer experience look like? Then explore how it can be delivered to millions of customers in a scalable way.

We are **not** asked to build "just another feature", but a **vision + proof of concept** of a scalable personalization approach that fundamentally strengthens the relationship between KBC and its customers.

Guiding questions from the organisers:

1. What signals can help us understand what customers need?
2. How can customers be recognized based on their situation, behavior and intent?
3. How can personalized experiences automatically adapt to each customer?
4. How can this work seamlessly across products, services and channels?
5. How can we create meaningful impact for millions of customers at the same time?

## How we are judged

| Criterion | Weight | Question |
|---|---|---|
| Creativity / originality | 30% | How original is the idea? |
| Technical ability | 30% | Does it work? |
| Fit to the challenge | 30% | Did we solve the challenge? |
| Security | 10% | How secure is it? (Aikido AI Code Audit, before/after screenshots) |

Submission (via Builderbase): short description, **demo video (< 3 min)**, this GitHub repo link, Aikido screenshots.

## Our solution

_TODO – fill in once the team picks a direction. See [docs/ideas.md](docs/ideas.md) for the brainstorm._

**Base app (ready):** a KBC-Mobile-style banking app to build the PoC on. Synthetic customers can log in, see accounts and transactions, make transfers, and get a **"Voor jou"** feed of personalised, explainable insights ("Waarom zie ik dit?"). The personalization engine plugs in at [`backend/app/services/insights.py`](backend/app/services/insights.py).

## Architecture

```
Browser (React + Vite + TS, mobile-first)
   │  same origin, HttpOnly SameSite=Strict session cookie
   ▼
FastAPI (Python 3.13) ── /api/v1/*  → routers → Bank (owner-scoped data) + insights rules
   └─ serves the built SPA from /       (one container → one Cloud Run service)
```

| Folder | What |
|---|---|
| `backend/` | FastAPI API, domain logic, synthetic data seed, pytest suite |
| `frontend/` | React SPA (see `frontend/README.md`) |
| `docs/api.md` | API contract between frontend and backend |
| `Dockerfile` | Multi-stage build: Node builds the SPA, slim non-root Python image runs it |
| `deploy/cloudrun.sh` | One-command deploy to Google Cloud Run |

**Security by design** (Aikido audits business logic, IDOR, authn, authz):
- Every data query takes the logged-in user's id (`Bank.account_for(owner_id, ...)`): other users' data is unreachable by construction and returns the same `404` as a non-existent id.
- Server-side sessions (random token, only its hash stored, revoked on logout, rotated on login) in an `HttpOnly; Secure; SameSite=Strict` `__Host-` cookie. No tokens in JS/localStorage.
- scrypt password hashing, constant-time compare, timing-equalised unknown users, login rate limiting (429).
- Server-side validation of every transfer: IBAN mod-97, amount > 0, 2 decimals, max € 10 000, sufficient funds, no same-account or credit-card transfers.
- CSRF guard (JSON-only + Origin check) on top of SameSite, strict CSP and security headers, no API docs in production, validation errors never echo input.
- Secrets only via env / Google Secret Manager; container runs as non-root with a read-only filesystem in compose.
- CI: ruff, mypy (strict), pytest, ESLint, tsc, vitest, `pip-audit`, `npm audit`, Docker build; Dependabot for all ecosystems.

## How to run

**Prerequisites:** Python 3.13, Node 24 (or only Docker).

```bash
cp .env.example .env          # then set DEMO_PASSWORD (min 8 chars)
```

**Option A – Docker (production-like):**
```bash
docker compose up --build     # http://localhost:8080
```

**Option B – dev mode with hot reload (two terminals):**
```bash
# terminal 1 – API on :8000
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows (PowerShell): .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --env-file ../.env

# terminal 2 – web on :5173 (proxies /api to :8000)
cd frontend
npm ci && npm run dev
```
Log in as `emma`, `jan` or `marie` with your `DEMO_PASSWORD`. API docs (dev only): http://localhost:8000/api/docs

**Checks (same as CI):**
```bash
cd backend && ruff check . && ruff format --check . && mypy app && pytest
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

**Deploy to Google Cloud Run:**
```bash
gcloud auth login
PROJECT_ID=<your-gcp-project> ./deploy/cloudrun.sh
```

## What is unfinished / known limitations

- **Data is in memory and synthetic.** It resets on every restart; that is why Cloud Run runs with `--max-instances 1`. Next step: a Firestore/Cloud SQL implementation of `Bank` and a shared session store.
- **Demo login:** all personas share one password from `DEMO_PASSWORD`. No MFA/itsme – out of scope for the PoC.
- **Insights are simple rules**, not yet ML/LLM – this is where the PoC's personalization engine goes.
- Rate limiting is per instance (in memory).

## Team & contributing

New here? Start with **[ONBOARDING.md](ONBOARDING.md)** (10 minutes), then read [CONTRIBUTING.md](CONTRIBUTING.md).

## Rules we must respect

- Build only during the official hackathon slot; final submission = final (no changes afterwards).
- Keep this repository **public** and accessible until judging is complete.
- **Never commit** passwords, API keys, tokens or confidential/real customer data. Use synthetic data only.
- No plagiarism; be respectful.
