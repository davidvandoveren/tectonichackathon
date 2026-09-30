# Brainstorm – KBC personalization at scale

Status: **direction chosen (see below)**, still open for input. Add your ideas via PR or directly under [Parking lot](#parking-lot).

## Framing

The brief asks for a *scalable approach to understanding, supporting and guiding customers*. Every idea is built from the same four layers; what differs is the "hero" experience we demo.

```
Signals → Understanding (situation / behavior / intent) → Decision (what, when, which channel) → Experience (adapts per customer)
   ▲                                                                                           │
   └──────────────────── feedback + consent + explainability ◀─────────────────────────────────┘
```

**Design principles:** privacy & consent first · explainable ("why am I seeing this?") · human in control · cheap at 2.3M customers (expensive models only where they add value) · works across app, web, branch, advisor and voice.

## Chosen direction: Kate as a proactive guide

Kate is already KBC Mobile's digital assistant. Today she mostly *reacts*. Our PoC turns Kate into a guide that **recognises the right moment, prepares the work, and explains why**, so the customer only has to confirm.

> From "ask Kate" to "Kate already knows what you need next, and tells you why."

This merges our strongest candidates into one story: the Moments Engine (old idea 1) is Kate's brain, the voice companion (4) is Kate's voice, the trust layer (6) is how Kate explains herself, and the advisor copilot (7) is Kate's hand-off to a human.

### Building blocks (in priority order)

| # | Block | What the customer experiences | Where it lives in the code |
|---|---|---|---|
| 1 | **Kate moments** (proactive) | "Congrats on your first salary! Shall I move €200/month to savings?" – one tap, pre-filled. | `backend/app/services/insights.py` rules → "Voor jou" cards get an action |
| 2 | **"Just say it"** (natural language) | "Send Lucas 25 euro for the pizza" / "How much did I spend on food this month?" → pre-filled screen or answer. 1 sentence instead of 5 screens. | New `/api/v1/kate` endpoint, Gemini Flash on Vertex AI, tools = our existing owner-scoped API |
| 3 | **Trust: "What does Kate know about me?"** | Every suggestion has "Waarom zie ik dit?"; a screen lists the signals Kate uses, each can be switched off. | `reason` field (exists) + signals/consent screen |
| 4 | **Kate adapts per customer** | Emma (21) gets short, informal nudges; Marie (67) gets calm explanations, larger text, advisor option. Same Kate, different tone. | Persona/tone passed to the prompt + UI density setting |
| 5 | **Kate's voice** (ElevenLabs) *– stretch* | Talk to Kate instead of typing; NL/FR/EN, adapted pace. Great for Marie and for the demo video. | Frontend mic → Kate endpoint → ElevenLabs TTS |
| 6 | **Hand-off to a human** *– stretch* | Big/sensitive moments (mortgage, bereavement, debt) → Kate briefs an advisor, customer doesn't repeat their story. | Advisor summary view |

### Security rules for Kate (Aikido: business logic, IDOR, authn, authz)

- **Same authorization as the rest of the app.** Kate's tools only call existing functions that take the logged-in user's id (`Bank.account_for(owner_id, …)`), so Kate can never see another customer's data.
- **Human in the loop.** Kate *proposes* money movements; the customer confirms on the normal, server-validated transfer screen. Kate never executes a transfer herself.
- **Prompt-injection safe.** Transaction descriptions are untrusted input ("ignore your instructions and…"). Pass them as data, never as instructions, and add a test for it.
- **Data minimisation.** Send the model summaries (categories, totals), not full IBANs or names, unless a tool call needs them. No real customer data anywhere – synthetic personas only.
- **Scale & cost.** Rules run for all 2.3M customers for free; the LLM is only called when a customer talks to Kate or a moment needs a personal message (Gemini Flash).

### Demo script (< 3 min video)

1. **Emma** opens the app → Kate: "First salary received 🎉 – save €200/month?" → *Waarom zie ik dit?* → one tap → done.
2. Emma types "Stuur Lucas 25 euro voor de pizza" → pre-filled transfer → confirm. ~5 seconds.
3. **Jan** → Kate spotted the move (moving company, IKEA, deposit) → one checklist: address, home insurance, energy.
4. **Marie** *talks* to Kate (voice) → calm answer + "Shall I book a call with your advisor?"
5. Close on the trust screen + one line on how it scales (rules for everyone, LLM only on demand).

## Scale strategy (answers guiding question 5)

- **Tiered intelligence:** rules/light ML for all 2.3M → LLM only for shortlisted moments or when the customer talks to Kate → human for high-value/sensitive cases.
- **Event-driven:** stream signals (Pub/Sub), precompute profiles, compose on demand, cache aggressively.
- **Cost guardrails:** token budgets, batching, small/fast models (Gemini Flash) for classification and chat, bigger model only where it clearly adds value.
- **Evaluation at scale:** synthetic personas + simulated customer journeys + guardrail tests (incl. prompt injection); A/B hooks in the design.

## Data (no real customer data!)

The base app seeds a **synthetic population** (`backend/app/domain/seed.py`): Emma (first salary), Jan (moving house), Marie (retired, idle savings). Seeds are reproducible so everyone's demo looks the same. Add personas there for new moments.

## Tech stack (decided)

- Backend: Python 3.13 + FastAPI · Frontend: React + Vite + TypeScript
- One Docker image → Google Cloud Run (`deploy/cloudrun.sh`), secrets in Secret Manager
- AI: Gemini Flash on Vertex AI for Kate, ElevenLabs for voice; Cursor for coding
- Security: Aikido AI Code Audit early (baseline) and again at the end (10% of score)

## Other ideas we considered

Kept for reference; the useful parts are folded into Kate above.

| Idea | Creativity | Technical | Fit | Feasible | Status |
|---|---|---|---|---|---|
| 1 Moments Engine (life-event detection) | 3 | 4 | 5 | 5 | → Kate block 1 |
| 2 Customer Context Graph + Journey Composer | 3 | 5 | 5 | 3 | Vision slide / "how it scales" |
| 3 Generative UI ("an app per customer") | 4 | 4 | 4 | 4 | Partly → Kate block 4 |
| 4 Proactive voice companion (ElevenLabs) | 5 | 3 | 3 | 4 | → Kate block 5 |
| 5 Financial Twin (what-if simulations) | 4 | 3 | 3 | 3 | Parked – advice-boundary risk |
| 6 Trust layer (consent, "why this?") | 4 | 3 | 4 | 5 | → Kate block 3 |
| 7 Advisor copilot | 3 | 3 | 4 | 4 | → Kate block 6 |

## Open questions

- Who owns what? Suggested split: **Kate backend** (endpoint + Gemini + tools) · **Kate UI** (Kate bar, action cards, trust screen) · **moments & personas** (rules + seed data) · **voice** · **demo video + Aikido pass**.
- Kate language: Dutch only, or NL/FR/EN from the start?
- Do we deploy to Cloud Run for the demo, or record locally?

## Parking lot

_Drop new ideas here (one line each, with your name) – we'll sort them in._
