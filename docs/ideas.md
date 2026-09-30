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

## Kate 2.0 – additions from Sander's team briefing

Same direction as above, framed as **the brain behind the next generation of Kate**. Today Kate works from 140+ predefined situations. Kate 2.0 understands customers through their *situation, needs and timing* instead of loose rules. We show it inside a simulated KBC Mobile environment and build no new app. Goal: a **stronger relationship**, not more product sales.

### Three pillars

1. **Pick up signals:** transactions, in-app behavior, life events, and what the customer tells Kate.
2. **Recognise situation and needs:** life phase plus what is going on right now.
3. **Right moment, right channel:** feed card, push, SMS/mail, or even a phone call.

### Feature ideas (with their guardrails)

| Feature | Idea | Guardrails |
|---|---|---|
| **a. Urgency meter** | Every action gets an urgency score. More urgent means a more direct channel: feed card → push → SMS/mail → (optional) **AI phone call** via ElevenLabs. | Always say it's an AI (AI Act Art. 50, in force since 2 Aug 2026). Kate says so at the start of every call. Call only with per-channel opt-in and only at high urgency. **Show when Kate deliberately sends nothing**, because not spamming is a feature. |
| **b. Transaction tracker** | Categorise transactions, spot patterns and life events (new salary, rent disappears, salary missing, big purchase), then make suggestions. | **Never infer or label sensitive categories** (health, religion, politics, trade union, sexual orientation): label them "other", and they never feed the profile. Descriptions are untrusted data, never LLM instructions. |
| **c. Big financial decisions** | Buying a home, inheritance, moving in together, first job, retirement: a tailored step plan, info gathering, explanation, preparation. Example: *"my mother died, what do I do with the inheritance?"* → Kate switches to a **guidance mode** (step plan, documents, no marketing). | **The decision always stays with a human**: Kate prepares a hand-off to a KBC advisor with full context. **Access to the deceased's products only after heir verification** (an authorization check, relevant for Aikido). |
| **d. Investing** | Explain strategies, help the customer understand their own situation and risk profile, prepare for an advisor meeting. | Neutral and educational, no "buy X" advice (MiFID, suitability test). Portfolio management is at most a concept with explicit consent + human advisor, and never autonomous trading. |
| **e. Subscription manager** | Detect recurring payments: price increases, duplicate subscriptions ("two streaming services with the same offer"), forgotten trials that became paid. Saves the customer money with data the bank already has. | The bank doesn't know usage, so never guess it. Ask *"Do you still use this?"* with *yes / no, remind me to cancel*. Don't analyse subscriptions in sensitive categories (health apps, religious/political orgs, trade union, dating). |

> **Status d. Investing + a. urgency (automation): ✅ first version ready** (issue #66). *Beleggen met Kate* (`/invest`): health check with a buffer that is never invested → questions → a direction (defensive/neutral/dynamic) → the customer picks ETFs from a demo catalogue (Kate marks fit and warns, never picks) → monthly steps from savings to Bolero, confirmed by the customer and executed by Kate, pausing instead of touching the buffer. Kate's chat explains investing freely but never names a real product to buy. *Kate sends by herself*: a background dispatcher turns the engine's decisions into notifications (bell + inbox + toast, each with "Waarom kreeg ik dit?").

### f. Family circle – linked accounts (idea: Sander)

> **Status: ✅ first version ready** (Sander · Claude session, issue #28). Page `/family` (Profiel → Familiekring), API in [docs/api.md](api.md#family-circle--linked-accounts-family).
> Works: invite → accept (mutual consent), per-link sharing (`exists` < `gift` < `pot` < `balances`), end any time, shared pots with contributions via the normal transfer rules, registry guardianship that ends automatically at 18 (try the time machine on Jan/Noor), Kate suggestions with *Waarom zie ik dit?*. Demo: log in as **marie** (contribute to Emma's wedding pot), **jan** (sees Noor's balances until she turns 18), **noor** after the time machine.
> Not yet: heir verification / death, "care for older parents" alerts, joint accounts, removing members from a pot, circle signals feeding the Moments Engine.

Customers can **link their KBC accounts to the people around them**: fiancé(e), spouse/partner, child, grandchild, godchild, mother, father, step-parents, and so on. This creates an **"organic" environment where everything fits together**. Kate understands the customer as part of a family, not as a loose individual, and helps across the whole circle at the right moments.

**What Kate does with it (examples):**
- **Parents and children:** at the right moments Kate suggests options for the child: start a savings account at birth, pocket-money account with parental controls at 12, first own card at 16, first job / student job at 18, help with a first home deposit later.
- **Grandparents / godparents:** "Your godchild turns 18 next month. Want to set up a gift to their savings account?" (only if both sides agreed to the link).
- **Engaged / married / living together:** share a **joint account** or a shared "pot" (rent, groceries, holiday) next to their own accounts. Kate helps both: splits costs, sets up a savings goal for the wedding or a house, and prepares the talk with an advisor about a joint mortgage or marriage contract.
- **Life events ripple through the circle:** a birth, a wedding or a death in the family shows up for the linked people with relevant (and respectful) guidance. Example: the inheritance guidance mode (feature c) knows who the heirs in the circle are, but still requires heir verification.
- **Care for older parents:** an adult child can, with explicit permission, get limited visibility to help a parent (e.g. alert on unusual payments = fraud protection), without taking over control.

**Boundaries (every link has its own, within legal limits):**
- **Mutual, explicit consent** for every link. Both sides accept, and each can end the link at any time. A link is never inferred from transactions ("these two send each other money, so they're a couple" is **not** allowed).
- **Granular sharing per link:** seeing nothing / seeing only that the link exists / seeing a shared pot / seeing balances / being able to act. Default = minimum. Linking ≠ seeing everything.
- **Minors:** parents/legal guardians have legal authority over a minor's account, and that ends automatically at **18**. The child then decides what the parent may still see. Kate addresses children in age-appropriate language and does no marketing to minors.
- **Joint accounts:** both holders see the same thing. Kate's suggestions about a joint account go to **both**, never "secretly" to one of them. Personal accounts stay private, even for a spouse.
- **Protection against abuse:** in case of divorce, conflict or financial abuse, one partner can end sharing immediately without the other being able to block it. Kate never nudges one person to give another person access. Watch for elderly people being pressured into giving access.
- **Death:** a link gives **no** automatic access to a deceased person's products. Heir verification still applies (feature c).
- **Sensitive data never flows through the circle:** sensitive categories (health, religion, etc.) are never shown to linked people, not even to a parent or spouse.
- **Security (Aikido):** every endpoint checks server-side that the logged-in customer has an **active, consented link with the right permission level** for the other person's data. This is a classic IDOR/authorization risk, so it's a strong showcase for the security score.

**Demo idea:** a young couple links accounts → they get a shared "Wedding" pot → Kate proposes a savings plan to both → their parent (linked, only "gift" permission) gets the option to contribute. Or: a child turns 18 → the parent's access ends automatically and Kate asks the child what may still be shared.

### Privacy and ethics rules (GDPR / AI Act)

- ✅ Use the customer's own KBC data to help that customer, transparently.
- ✅ Use what the customer tells Kate only for the purpose they told it for, never for unsolicited marketing.
- ✅ Every suggestion has **"Waarom zie ik dit?"**.
- ✅ **Consent toggles** per signal type and per channel. Always respect an objection to marketing profiling.
- ⚠️ Credit or investment proposals: only with a human advisor, and never pushing people who are in financial difficulty.
- ❌ No sensitive inferences, no manipulation or dark patterns, no exploiting vulnerability, no social scoring, no discrimination via proxies (postcode, name).
- ❌ Don't store emotions ("customer is depressed"); adapting tone is fine.
- ❌ No fully automated decisions with big consequences (e.g. refusing credit).

Pitch line: *"a bank you dare to tell about such a moment, because you know it helps you and doesn't profit from it."*

### Demo elements

- **Time machine:** a "fast-forward 1 week" button (admin-only endpoint) that injects new transactions so Kate reacts live. This is the most important demo element.
- **Jury dashboard:** per persona signal → recognised situation → chosen action → reason, plus an overview across **10,000 synthetic customers** (how many got which action, and how many deliberately got nothing).
- **Synthetic data:** 5–8 detailed personas with 6–12 months of transactions and built-in life moments (student with first job, young couple, inheritance scenario, financially tight, retiree), plus a 10k-customer mode to show scale.
- **Mock KBC Mobile UI:** our own design with a clear "concept/prototype" label, **no copied KBC logos or assets**.

Demo flow (< 3 min): (1) two personas side by side, same app, very different Kate → (2) time machine: salary doesn't arrive, Kate reacts via the right channel on the urgency meter → (3) customer tells Kate about an inheritance, Kate guides end-to-end with advisor hand-off → (4) subscriptions: "you're paying twice for the same thing, do you still use this?" → (5) dashboard: "this is what it looks like for 2.3M customers", including how many got nothing.

### Extra security points from the briefing

- Real login per persona (even in the demo), correctly validated session/JWT.
- **Every** endpoint checks server-side that the data belongs to the logged-in customer (never trust an ID from URL/body).
- Heir verification before access to someone else's products.
- Time-machine and admin endpoints (dashboard, data generation) only for a separate **admin role**.
- Pydantic input validation, **rate limiting on LLM endpoints**.
- Transaction texts and chat messages treated as data, not instructions.

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

- (Sander) Merge the demo scripts: David's (Emma/Jan/Marie, "just say it") and the briefing's (time machine, inheritance, subscriptions, 10k dashboard). Which 3 features do we make really work?
- (Sander) Add personas for the briefing's scenarios: financially tight (salary missing), inheritance, young couple, duplicate subscriptions.
