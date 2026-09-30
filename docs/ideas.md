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

### Positioning: what is actually new *(verified 2026-09-30)*

One thing to get right before the pitch, because the jury **is** KBC: Kate has been live since **November 2020** and already proactively covers **more than 140 situations** for **5.8 million** digital customers, solving **70%** of queries on her own ([source](https://newsroom.kbc.com/kate-your-personal-digital-assistant/)). So "a bank that reaches out proactively" is not our idea — they shipped it six years ago. We must not pitch it as new.

What *is* new is how those situations come into being. 140 situations are **hand-authored**, and you cannot hand-author a segment-of-one for 2.3M customers — which is exactly guiding question 5.

> **Kate's situations are written. Ours are composed.**
> A catalogue of cheap, reusable **signals** combines into **moments** nobody pre-programmed, each with a confidence score.

And that has a consequence worth leaning on: once moments arise combinatorially instead of being written one by one, **arbitration** — deciding what is worth saying, when, through which channel, and when to stay silent — stops being a nicety and becomes the core of the system. That is the part no one else will build.

### Building blocks (in priority order)

| # | Block | What the customer experiences | Where it lives in the code |
|---|---|---|---|
| 1 | **Kate moments** (proactive) | "Congrats on your first salary! Shall I move €200/month to savings?" – one tap, pre-filled. | `backend/app/moments/` (engine) → `backend/app/services/insights.py` (adapter) → "Voor jou" cards get an action |
| 2 | **"Just say it"** (natural language) | "Send Lucas 25 euro for the pizza" / "How much did I spend on food this month?" → pre-filled screen or answer. 1 sentence instead of 5 screens. | New `/api/v1/kate` endpoint, Gemini Flash on Vertex AI, tools = our existing owner-scoped API |
| 3 | **Trust: "What does Kate know about me?"** | Every suggestion has "Waarom zie ik dit?"; a screen lists the signals Kate uses, each can be switched off. | `reason` field (exists) + `/api/v1/trust/*` (signals + consent) |
| 4 | **Kate adapts per customer** | Emma (21) gets short, informal nudges; Marie (67) gets calm explanations, larger text, advisor option. Same Kate, different tone. | Tone selected by the engine's composition layer + UI density setting |
| 5 | **Kate's voice** (ElevenLabs) *– stretch* | Talk to Kate instead of typing; NL/FR/EN, adapted pace. Great for Marie and for the demo video. | Frontend mic → Kate endpoint → ElevenLabs TTS |
| 6 | **Hand-off to a human** *– stretch* | Big/sensitive moments (mortgage, bereavement, debt) → Kate briefs an advisor, customer doesn't repeat their story. | Advisor summary view |

### Extra moments for block 1 *(approved 2026-09-30 – specced in [docs/design/moments-engine.md](design/moments-engine.md))*

**A. Automate the habit the customer already has**

Some customers move money from their current account to savings **by hand**, most months, a few days after their salary lands. That is a behaviour, not a life event – and it is visible in the data. Detect the pattern and offer to turn it into a standing order (*bestendige opdracht*), using the customer's **own** numbers: the median amount they already transfer, at the median lag after their salary date.

- Confidence comes from the regularity itself: months with a transfer ÷ months observed, penalised by amount variance. No hand-written threshold.
- Counter-evidence matters: if the customer has ever moved money *back* out of savings, they need that liquidity – stay silent. Locking it away would hurt them.
- Note for the demo script below: this makes Emma's "€200/month" a number **derived from her own behaviour** instead of one the bank picked. Same screen, much stronger claim.

**B. Match real behaviour to the real product catalogue – in both directions**

Scan spending and match it against KBC's **actual** offer, not an invented one. Two facts to know first: KBC has **discontinued** Silver/Gold/Platinum (a single `KBC-Kredietkaart` remains, migration runs April 2025 → April 2027, and the insurances that were standard on the old cards **lapse on replacement**), and there is **no KBC fuel or loyalty-points programme**. The real hooks are the optional packages (Shoppingpakket € 1,50/mo · Reispakket € 7,00/mo · Luxepakket € 25,00/mo) and Kate Deals. So:

- **Missing cover:** travel bookings but no Reispakket → suggest it, quantified from their own trips. Especially relevant for migrated customers whose old standard insurance silently lapsed.
- **Wasted cover:** paying € 25/mo for Luxepakket with zero travel or lounge activity → suggest **dropping** it. € 300/year back. A bank that costs itself money is the strongest trust signal we can demo, and it is in character: Kate already down-sells car insurance.
- **Kate Deals:** frequent fuel-ups at one station → surface the matching cashback deal (KBC's real mechanic: cashback credited on the first business day of the month), with the expected annual value in euros. The engine's job is not the deal – it is picking *which* deal for *whom*, and proving the value before showing it.
- Arbitration rule worth stating out loud to the jury: a suggestion that **costs** the customer money is suppressed when their buffer is thin; a suggestion that **saves** them money never is.

### Security rules for Kate (Aikido: business logic, IDOR, authn, authz)

- **Same authorization as the rest of the app.** Kate's tools only call existing functions that take the logged-in user's id (`Bank.account_for(owner_id, …)`), so Kate can never see another customer's data.
- **Human in the loop.** Kate *proposes* money movements; the customer confirms on the normal, server-validated transfer screen. Kate never executes a transfer herself.
- **Prompt-injection safe.** Transaction descriptions are untrusted input ("ignore your instructions and…"). Pass them as data, never as instructions, and add a test for it.
- **Data minimisation.** Send the model summaries (categories, totals), not full IBANs or names, unless a tool call needs them. No real customer data anywhere – synthetic personas only.
- **Scale & cost.** Rules run for all 2.3M customers for free; the LLM is only called when a customer talks to Kate or a moment needs a personal message (Gemini Flash). The moments engine itself stays fully deterministic, so the proactive demo cannot fail on a network call.

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
- **Measured, not claimed:** `backend/scripts/benchmark.py` runs the engine over N synthetic customers and prints p50/p95/p99 and the extrapolated cost of 2.3M. Everyone else will *say* their design scales.

## Data (no real customer data!)

The base app seeds a **synthetic population** (`backend/app/domain/seed.py`): Emma (first salary), Jan (moving house), Marie (retired, idle savings), and Sofie (manual savings habit, concentrated fuel spend, unused Luxepakket – added for the moments above). Seeds are reproducible so everyone's demo looks the same. Add personas there for new moments.

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
  - **moments & personas: claimed by Alexandre** (`backend/app/moments/`, `insights.py`, `seed.py`) – see [the design doc](design/moments-engine.md). Nobody else should edit those four files without a heads-up.
- Does the frontend consume the new `GET /api/v1/experience` (blocks + tone + what Kate stayed silent about), or only the enriched `/api/v1/insights`? `/insights` keeps its current shape either way, so this is not blocking.
- Kate language: Dutch only, or NL/FR/EN from the start?
- Do we deploy to Cloud Run for the demo, or record locally?

## Parking lot

_Drop new ideas here (one line each, with your name) – we'll sort them in._
