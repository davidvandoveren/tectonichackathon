# Design – Moments Engine

Status: **approved for implementation** · Date: 2026-09-30 · Owner: Alexandre C
Scope: `backend/app/moments/` (new), `backend/app/services/insights.py` (becomes an adapter),
`backend/app/domain/seed.py` (one new persona). Does **not** touch `frontend/`.

## 1. Why this exists

The challenge asks for a *scalable* personalization approach, and judges 30% creativity,
30% technical ability, 30% fit and 10% security.

KBC already ships proactive personalization: **Kate** has been live since November 2020 and
proactively suggests solutions in **more than 140 situations** for 5.8 million digital customers,
solving 70% of queries on her own. So "a bank that reaches out proactively" is not the idea —
KBC has it.

The gap is *how those situations come into being*. 140 situations are hand-authored. You cannot
hand-author your way to a segment of one for 2,300,000 customers; that is exactly guiding
question 5. So:

> **Kate's situations are written. Ours are composed.**
> A catalogue of cheap, reusable **signals** combines into **moments** that nobody
> pre-programmed, each carrying a confidence score. Because moments now arise
> combinatorially instead of being written by hand, an **arbitration** layer stops being a
> nicety and becomes the core of the system: something has to decide what is worth saying,
> when, through which channel — and when to say nothing at all.

Everything in this design is deterministic Python. No LLM, no network call, no API key on the
critical path, so the demo cannot fail live in front of a jury.

### 1.1 How this maps to the team's Kate blocks

The team's chosen direction is *Kate as a proactive guide* (see `docs/ideas.md`). This engine is
the brain behind it, and it lines up with the agreed building blocks:

| Kate block | Served by |
|---|---|
| 1 – Kate moments (proactive) | layers 1–3: signals, moments, arbitration |
| 3 – Trust: "what does Kate know about me?" | `GET /api/v1/trust/signals`, `PUT /api/v1/trust/consent` |
| 4 – Kate adapts per customer | layer 4: composition and tone selection |
| 6 – Hand-off to a human *(stretch)* | the `advisor_task` channel that arbitration can select |

Block 2 (Kate's natural-language chat, Gemini Flash on Vertex AI) and block 5 (ElevenLabs voice)
are **not** part of this design and are owned separately. The split matters: the *conversational*
side of Kate may call a model, but the *proactive* side — the part the demo video opens with —
stays deterministic, so it cannot fail on a network call in front of the jury.

Ownership per `docs/ideas.md`: `backend/app/moments/`, `backend/app/services/insights.py`,
`backend/app/domain/seed.py` and `backend/scripts/`. Nothing in `frontend/`.

## 2. Architecture

```
Transactions + accounts
        │
        ▼
  [1] SIGNALS ─────── cheap, computed for everyone, consent-gated per domain
        │             typed evidence with a strength in [0,1]
        ▼
  [2] MOMENTS ─────── weighted combinations of signals -> confidence in [0,1]
        │             a moment is never a single threshold
        ▼
  [3] ARBITRATION ─── what, when, which channel, or deliberate silence
        │             the tiered-intelligence and anti-spam layer
        ▼
  [4] COMPOSITION ─── ordered UI blocks from a fixed safe vocabulary + tone
```

Files under `backend/app/moments/`:

| File | Responsibility |
|---|---|
| `signals.py` | `Signal` type + one pure extractor per signal |
| `moments.py` | `Moment` type + one pure detector per moment |
| `arbitration.py` | ranking, suppression, cooldown, channel choice, silence reasons |
| `composition.py` | block assembly, tone selection, copy variants |
| `catalog.py` | KBC product facts (card packages, deal categories) as data |
| `engine.py` | the single public entry point |

Each layer is a pure function of its input. That is what makes it testable, cheap and
explainable — and it is why the benchmark in section 8 is meaningful.

## 3. Data model

```python
Domain = Literal["income", "spending", "balances", "products"]

@dataclass(frozen=True)
class Signal:
    type: str            # e.g. "deposit_like_outflow"
    domain: Domain       # which consent toggle gates it
    strength: float      # 0..1, how strong this evidence is
    observed_at: date
    evidence: str        # plain Dutch, shown in the trust panel
    meta: Mapping[str, str]   # amounts, counterparties, for composition

Urgency = Literal["risk", "obligation", "opportunity"]

@dataclass(frozen=True)
class Moment:
    type: str
    confidence: float     # 0..1, weighted from contributing signals
    urgency: Urgency
    signals: tuple[Signal, ...]
    value_eur_per_year: Decimal | None   # estimated impact, drives ranking
    meta: Mapping[str, str]

Channel = Literal["passive_card", "home_hero", "push_notification", "advisor_task"]

@dataclass(frozen=True)
class Decision:
    moment: Moment
    channel: Channel

@dataclass(frozen=True)
class Silence:
    moment_type: str
    reason_code: str      # e.g. "cashflow_first", "low_confidence", "dismissed", "quota"
    reason: str           # plain Dutch

@dataclass(frozen=True)
class Composition:
    blocks: tuple[Block, ...]
    tone: Literal["simple", "plain", "formal"]
    decisions: tuple[Decision, ...]
    silenced: tuple[Silence, ...]
```

`silenced` is a first-class output, not an empty list. The demo can show, on screen, that the
bank found something and chose not to speak — and why.

## 4. Signal catalogue

All derived from the customer's own history. No cross-customer data, no keyword lists standing
in for logic.

| Signal | Domain | Derivation |
|---|---|---|
| `new_income_payer` | income | income counterparty absent from history older than 30d |
| `income_step_up` | income | recent max income / median historical income >= 2 |
| `income_recurring` | income | same income counterparty >= 2 months, low day-of-month variance |
| `pension_income` | income | recurring income from a pension authority pattern |
| `large_outflow_outlier` | spending | outflow >= 4x the 90th percentile of that category's history |
| `category_spend_spike` | spending | last 30d category total >= 2x the prior 60d monthly average |
| `deposit_like_outflow` | spending | single housing outflow within 10% of 2x or 3x median monthly rent |
| `merchant_concentration` | spending | one counterparty >= 6 bookings in 90d **and** >= 40% of its category |
| `recurring_self_transfer` | spending | >= 3 current->savings transfers in 90d on a monthly cadence |
| `reverse_savings_transfer` | spending | any savings->current transfer (**counter-evidence**) |
| `travel_spend` | spending | bookings at travel/airline/hotel/car-rental counterparties |
| `subscription_detected` | spending | recurring monthly booking under EUR 50 at the same counterparty |
| `idle_liquidity` | balances | savings balance >= 12x the last 30d spend |
| `thin_buffer` | balances | current balance < the largest upcoming recurring obligation |
| `paid_package_unused` | products | holds a paid card package with no matching activity in 90d |

### Why this beats the current rules

`insights.py` today detects a house move by matching `verhuis`, `ikea` or `waarborg` in the
counterparty name. That collapses the first time a customer buys furniture at Leen Bakker, uses a
different mover, or lives in Wallonia.

Here, a move is the *shape* of the spending: an outflow far above this customer's own normal, a
housing outflow that sits at about 2x their median rent (so it looks like a rental deposit), and
a spike in a discretionary category. Three independent pieces of evidence, no merchant list.

## 5. Moment catalogue

`+` contributes evidence, `-` is counter-evidence that lowers confidence.

| Moment | Urgency | Composed from |
|---|---|---|
| `cashflow_risk` | risk | `+thin_buffer` `+`upcoming obligation |
| `first_salary` | opportunity | `+new_income_payer` `+income_step_up` |
| `moving_house` | obligation | `+large_outflow_outlier` `+deposit_like_outflow` `+category_spend_spike` |
| `idle_savings` | opportunity | `+idle_liquidity` `-thin_buffer` |
| `savings_habit_automatable` | opportunity | `+recurring_self_transfer` `+income_recurring` `-reverse_savings_transfer` `-thin_buffer` |
| `card_package_gap` | opportunity | `+travel_spend` `-`holds Reispakket |
| `card_package_waste` | opportunity | `+paid_package_unused` |
| `deal_match` | opportunity | `+merchant_concentration` |

Confidence is the weighted sum of contributing signal strengths minus counter-evidence,
normalised to [0,1]. A moment is emitted only above the notice threshold (section 6).

### 5.1 `savings_habit_automatable`

The customer already moves money to savings by hand most months. The engine proposes turning it
into a standing order (*bestendige opdracht*) using **the customer's own behaviour as the
parameters**:

- **amount** = median of the observed transfers (not a bank-chosen number)
- **day** = median lag in days after the recurring salary date
- **confidence** = months with a transfer / months observed, penalised by amount variance

`reverse_savings_transfer` is deliberate counter-evidence: a customer who has ever pulled money
back out of savings needs that liquidity, and locking it into an automatic order would harm them.
The engine stays silent for them, and says so in the trust panel.

This is behaviour, not a life event — a pattern falling out of the data with a measurable
confidence, which is the compositional story in miniature.

### 5.2 `card_package_gap` and `card_package_waste`

KBC product facts as of 2026-09 (see section 11): Silver / Gold / Platinum tiers are
**discontinued** — existing holders are migrated to a single `KBC-Kredietkaart` between April
2025 and April 2027, and **the insurances that came standard with the old cards lapse on
replacement**. There is no KBC fuel or loyalty-points programme.

So the engine matches behaviour against the *real* optional packages:

| Package | Price | Covers |
|---|---|---|
| Shoppingpakket | EUR 1,50 / month | purchase protection, 2 extra years of warranty |
| Reispakket | EUR 7,00 / month | trip cancellation, rental-car franchise, delayed baggage |
| Luxepakket | EUR 25,00 / month | 24/7 Lifestyle & Travel Manager, airport lounges |

Both directions matter, and the second one is the differentiator:

- **`card_package_gap`** — travel activity, no Reispakket -> suggest it, quantified from the
  customer's own bookings ("je boekte 3 reizen dit jaar"). Extra relevance for migrated
  customers whose old standard insurance lapsed.
- **`card_package_waste`** — paying EUR 25/month for Luxepakket with no travel or lounge activity
  -> **suggest dropping it: EUR 300 a year back**.

A bank that costs itself money is the most trust-building thing we can demonstrate, and it is in
character: Kate already down-sells car insurance.

### 5.3 `deal_match`

Kate Deals is KBC's real cashback mechanic: pay with a KBC card, KBC Mobile or Payconiq and the
cashback is credited on the first business day of the month. No points, no coupons.

`merchant_concentration` picks up that a customer fuels up at the same station most weeks, and
the engine surfaces the matching deal category with an **expected annual cashback in euros**
derived from their actual spend. The engine's contribution is not the deal — it is choosing
*which* deal, for *whom*, and proving the value before showing it.

## 6. Arbitration policy

The layer that makes combinatorial moments safe. Concretely:

**Thresholds**

- `confidence >= 0.60` -> may be acted on
- `0.35 <= confidence < 0.60` -> **observed but silent**, surfaced in the trust panel as "we see
  something, we're not sure yet". Recorded as `Silence(reason_code="low_confidence")`.
- `< 0.35` -> discarded

**Ranking** — urgency tier first (`risk` > `obligation` > `opportunity`), then
`confidence * value_eur_per_year`.

**Quota** — at most **one** interruptive decision per customer per 7 days. Everything else
degrades to `passive_card`: visible if you look, never pushed.

**Suppression rules**

- Any active `risk` moment silences every `opportunity` moment ->
  `reason_code="cashflow_first"`. No investment pitch to someone who is short on rent.
- **Asymmetry:** a suggestion that *costs* the customer money (`card_package_gap`, `deal_match`)
  is suppressed when `thin_buffer` holds. A suggestion that *saves* them money
  (`card_package_waste`) is **never** suppressed.
- A dismissed moment is suppressed for 30 days -> `reason_code="dismissed"`.

**Channel selection**

| Condition | Channel |
|---|---|
| `risk` and confidence >= 0.8 | `push_notification` |
| `risk` otherwise | `home_hero` |
| `opportunity` / `obligation`, confidence >= 0.8 | `home_hero` |
| otherwise | `passive_card` |
| any moment with `value_eur_per_year > 500` and confidence >= 0.8 | **also** `advisor_task` |

We do not build four channels. We make the *decision* visible, which answers "seamlessly across
products, services and channels" without four front-ends.

## 7. Composition and trust

**Blocks** come from a fixed vocabulary — `hero_moment`, `insight_card`, `action_row`,
`balance_summary`, `deal_card`, `advisor_offer`, `trust_footer`. Copy comes from a variant table,
never free-form text: no invented numbers, no compliance exposure, no model in the loop.

**Tone** is `simple` / `plain` / `formal`, selected from data-derived signals (`pension_income`
-> `formal`; a low-volume student-job income pattern -> `simple`), not from a stored label.

**Consent** gates layer 1. Each signal declares a `domain`; a per-customer consent set filters
signals out *before* moments are detected. Switching off `spending` makes `moving_house`
disappear live, with an explanation. Stored in memory, matching the existing in-memory `Bank`.

Every moment can already explain itself: the `reason` field the current API guarantees is built
from the `evidence` strings of its contributing signals, so explainability is structural rather
than a hand-written sentence per rule.

## 8. Scale

`backend/scripts/benchmark.py` generates *N* synthetic customers, runs layers 1-3, and reports
p50 / p95 / p99 latency, throughput, and the extrapolated wall-clock and core-count to process
2,300,000 customers. Every other team will *claim* their design scales; this prints a number.
Run with a small *N* in CI so it cannot rot.

## 9. API — additive only

`frontend/` is being built in parallel, so nothing already in `docs/api.md` changes shape.

| Endpoint | Status |
|---|---|
| `GET /api/v1/insights` | **unchanged shape**, now fed by the engine (arbitrated and ranked). New optional fields: `confidence`, `urgency`, `signals` |
| `GET /api/v1/experience` | **new** — `blocks`, `tone`, `decisions`, `silenced` |
| `GET /api/v1/trust/signals` | **new** — signals used, with evidence and consent state |
| `PUT /api/v1/trust/consent` | **new** — toggle one domain |
| `POST /api/v1/experience/{moment_id}/dismiss` | **new** — feeds the 30-day cooldown, makes arbitration demonstrable |

Money stays a 2-decimal string, dates stay ISO 8601, auth stays the session cookie, and `404`
still means "not found *or* not yours". No new auth surface.

## 10. Synthetic data

No persona currently transfers to savings (the seed books everything on account 1) and none has a
concentrated merchant, so the three new moments have nothing to fire on.

Add **one** persona — `sofie`, 29, Antwerp, car commuter — who demonstrates all three at once:

- a manual current->savings transfer in most months, on a varying day a few days after salary
  -> `savings_habit_automatable`
- weekly fuel at one station -> `deal_match`
- pays for Luxepakket with no travel activity -> `card_package_waste`

This needs a small additive extension to `seed.py`: a `Habit` pattern (monthly, but with jitter
in day and amount) next to the existing fixed-day `Recurring`. One appended entry in `PERSONAS`,
so the conflict surface with parallel work in `backend/` stays minimal. Seeds stay fixed at 42 so
every demo looks identical.

## 11. Product facts and sources

Verified 2026-09-30. Recorded here so the claims in the demo are checkable:

- KBC credit card range and the Shopping / Reis / Luxe packages, incl. the discontinuation of
  Silver / Gold / Platinum and the lapse of standard insurance on replacement —
  <https://www.kbc.be/particulieren/nl/product/betalen/betaalkaarten/kredietkaarten-en-prepaid-kaarten/mastercard-kredietkaart.html>
  and <https://www.kbc.be/particulieren/nl/product/betalen/betaalkaarten/kredietkaarten-en-prepaid-kaarten/kredietkaart-silver-gold-platinum.html>
- Kate Deals cashback mechanic —
  <https://www.kbc.be/retail/en/products/payments/self-banking/on-your-smartphone/mobile/mobile-faq/deals.html>
- Kate: live since November 2020, 140+ proactive situations, 5.8M digital customers, 70% of
  queries solved autonomously — <https://newsroom.kbc.com/kate-your-personal-digital-assistant/>
  and <https://www.kbc.com/content/dam/kbccom/doc/newsroom/pressreleases/2025/20251124_Vijf%20jaar%20Kate_NL.pdf>

## 12. Testing

TDD, pytest, following the existing `backend/tests/` layout.

- one test per signal extractor, on hand-built fixtures — **not** on the seed, so these tests do
  not break when someone edits `seed.py`
- one test per moment detector, including the counter-evidence paths
  (`reverse_savings_transfer` must silence `savings_habit_automatable`)
- arbitration policy tests are the important ones: `cashflow_first` suppression, the
  save-money asymmetry, the 7-day quota, the 30-day cooldown, channel selection
- one golden test per persona asserting the expected top moment
- `ruff`, `ruff format`, `mypy app` must stay clean — CI already enforces all three

## 13. Build order

Every step leaves the repo shippable. If the clock runs out mid-list, what exists still works.

1. signals + tests
2. moments + tests
3. point `insights.py` at the engine (backward compatible) <- already better than `main` here
4. arbitration + silence
5. `GET /api/v1/experience`
6. trust / consent endpoints + dismiss
7. `seed.py`: the `sofie` persona
8. benchmark script
9. update `docs/api.md`, README (solution, how to run, honest limitations)

## 14. Out of scope

Deliberately not built, so the six hours go into one working thing: no LLM anywhere, no
ElevenLabs voice, no advisor copilot UI, no Financial Twin, no persistence beyond the existing
in-memory store, no new authentication. Voice is the first candidate if time is left over.

## 15. Open questions

- Will `frontend/` consume `GET /api/v1/experience`, or only the enriched `/insights`? Either
  works; the answer decides which one gets the polish.
- Who records the demo video, and which persona is the hero of it? `sofie` demonstrates three
  moments in one screen and is the strongest candidate.
