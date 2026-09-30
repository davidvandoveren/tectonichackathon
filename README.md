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

> **Kate's situations are written. Ours are composed.**

First, the thing we refuse to pretend: **a bank that reaches out proactively is not our idea.** Kate has been live in KBC Mobile since November 2020, already covers **140+ situations** for **5.8 million** digital customers and solves **70%** of queries on her own ([source](https://newsroom.kbc.com/kate-your-personal-digital-assistant/)). Pitching proactivity as new to a jury from KBC would be pitching them their own 2020 release.

What is new is **how a situation comes into being.** Those 140 situations are hand-authored, one at a time, by people. That works for 140. It cannot work for a segment-of-one across 2.3M customers — which is precisely guiding question 5. You cannot write 2.3M situations.

So we do not write situations. We write a catalogue of cheap, reusable **signals**, and let them **combine** into moments nobody pre-programmed, each carrying a confidence score derived from the customer's own regularity rather than a hand-picked threshold.

That has a consequence we lean on, because it is where the real engineering is: once moments arise combinatorially instead of being authored, **arbitration becomes the system.** Deciding what is worth saying, at what urgency, through which channel — feed card, push, SMS, call — and crucially **when to stay silent**, stops being a nicety. A bank that can generate a thousand relevant moments per customer and says nothing 999 times is more valuable than one that says all thousand.

### How this answers the challenge

| Guiding question | Our answer | Where it lives |
|---|---|---|
| 1. What signals reveal what customers need? | Signals derived from the customer's own bookings: income cadence, category patterns, recurring debits, buffer versus fixed costs. Cheap, explainable, no ML required. | [`backend/app/services/insights.py`](backend/app/services/insights.py) |
| 2. How to recognise situation, behaviour and intent? | Situation and behaviour are composed from those signals; **intent** the customer states directly, by talking to Kate in natural language. | [`backend/app/kate/`](backend/app/kate/), `POST /api/v1/kate/chat` |
| 3. How do experiences adapt automatically? | Every suggestion carries a plain-language `reason` ("Waarom zie ik dit?") that is **always** present, so the customer can see the evidence rather than trust a black box. The persona is passed to Kate as context; a dedicated tone layer per life phase is designed, not built. | `reason` on every insight, [`kate/context.py`](backend/app/kate/context.py) |
| 4. How does this work across channels? | One arbitration step turns an urgency score into a channel, and can choose to send nothing at all. | Moments engine (in review, see below) |
| 5. How does it reach millions? | **Tiered intelligence:** rule-based signals run for all 2.3M; an LLM is invoked only for a shortlisted moment or when the customer actually talks to Kate; a human advisor handles the high-value and sensitive cases. Cost scales with *conversations*, not with customers. | Design, see [docs/ideas.md](docs/ideas.md) |

### What works today

Try it yourself — one click, no password needed, synthetic data only: **[live demo](https://tectonichackathon-578474883491.europe-west1.run.app/login)**

| Capability | Status |
|---|---|
| KBC-Mobile-style app: login, accounts, transactions, transfers (IBAN mod-97, balance rules) | ✅ live |
| **"Voor jou"** feed: explainable insights, each with its own "Waarom zie ik dit?" | ✅ live |
| **Kate chat** in natural language, answering from the customer's own owner-scoped data | ⚠️ live, but on a **mock** responder — see below |
| **Kate's voice** (ElevenLabs) and speech input | ⚠️ built, **switched off** in the live demo |
| One-click persona login so judges can try all three customers instantly | ✅ live |

`GET /api/v1/kate/status` on the deployed service currently answers
`{"llm": "mock", "voice": false, "speech_recognition": false}`: the code degrades gracefully when no
credentials are present, and no Vertex AI or ElevenLabs key is set on Cloud Run yet. Kate answers,
but from a canned responder rather than Gemini. **Before the demo video, set those secrets** — the
endpoints are done, the keys are not.

### What is built but not yet merged

Honest status, because "does it work?" is 30% of the score and a promise is not a demo:

- **Moments engine** — signals → moments → urgency → channel → deliberate silence, plus a **time machine** that moves the clock so a reviewer can watch a moment fire instead of waiting a month. In review as PR #15.
- **Subscription manager** — price increases, duplicate subscriptions, forgotten trials that became paid, each answered with "Do you still use this?" rather than a guess, because the bank sees the payment and never the usage.

### Designed, not built

- Tone per life phase: Emma (21) short and informal, Marie (67) calm explanations and an advisor option.
- Consent screen ("What does Kate know about me?") with a switch per signal and per channel.
- Jury dashboard: signal → situation → action → reason, across a simulated population.
- Measured scale numbers (p50/p95/p99 and extrapolated cost for 2.3M). The tiering above is a design, not yet a benchmark, and we would rather say so than show a number we did not measure.

### Security, by construction

Security is 10% of the score, so it is a design input rather than a later pass. Every read and write of customer data goes through an ownership-scoped store that cannot answer "give me account X" without also proving whose it is, which rules out IDOR structurally rather than by review. Sessions are HttpOnly, `SameSite=Strict`, `__Host-`prefixed cookies; responses carry a strict CSP. Transaction descriptions and chat messages are treated as **data, never as instructions** to the model. And sensitive categories — health, religion, politics, trade union, dating — are never inferred, never profiled and never surfaced, which is a product decision as much as a privacy one. The Aikido baseline and final scans are still to be run.

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
- **Passwordless demo mode (on for the live demo):** with `PASSWORDLESS_LOGIN=true` anyone can open a synthetic persona with one click, so judges can try it instantly. It is off by default; sessions, owner-scoped access and all transfer rules still apply. Never enable it with real data.
- **Insights are simple rules**, not yet ML/LLM – this is where the PoC's personalization engine goes.
- Rate limiting is per instance (in memory).

## Team & contributing

New here? Start with **[ONBOARDING.md](ONBOARDING.md)** (10 minutes), then read [CONTRIBUTING.md](CONTRIBUTING.md).

## Rules we must respect

- Build only during the official hackathon slot; final submission = final (no changes afterwards).
- Keep this repository **public** and accessible until judging is complete.
- **Never commit** passwords, API keys, tokens or confidential/real customer data. Use synthetic data only.
- No plagiarism; be respectful.
