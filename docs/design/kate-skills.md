# Design – Kate Skills: one platform every KBC function plugs into

Status: **backend implemented** (PR `feature/kate-skills`) · Date: 2026-09-30 · Owner: David
Scope: `backend/app/skills/` (new), `backend/app/routers/skills.py` (new), two additive lines in
`backend/app/main.py`. Does **not** touch `frontend/`, `backend/app/moments/`,
`backend/app/kate/` or `seed.py`.

## 1. Why this exists

Three pieces of Kate 2.0 are being built in parallel:

| Piece | Where | Decides |
|---|---|---|
| Moments Engine (Chun) | `backend/app/moments/` | **when** and **for whom** something is worth saying |
| Kate chat + voice | `backend/app/kate/` (branch `feature/kate-assistant`) | what the customer **asks** for |
| **Kate Skills (this doc)** | `backend/app/skills/` | **what Kate can do**, and **what she is allowed to do** for this customer |

Today every capability is hard-coded where it is used: the chat has its own `transfer` /
`advisor_handoff` union, the engine plans its own product catalogue, the UI hard-codes
`cta_target`s. Adding one KBC product (travel insurance, a loan simulation, a Kate Deal) means
editing all three. That does not scale to KBC's full offer, and it means consent is checked in
three different places, or not at all.

> **Kate's situations are composed (Moments Engine). Kate's abilities are plugged in (Skills).**
> Every KBC function describes itself once — its actions, its risk, its guardrails — and becomes
> usable by every channel at once: proactive cards, chat, voice, push, advisor.

## 2. Core ideas

### 2.1 A skill is a KBC function that describes itself

A **skill** is one KBC domain (Betalen, Sparen, Kaarten, Kate Deals, Verzekeren, Lenen,
Beleggen, Adviseur). It owns a handful of **actions**. Each action declares:

- `id` (`"savings.move_to_savings"`), title, plain-Dutch description (also used as the LLM tool
  description)
- a **params model** (pydantic): the only shape Kate may fill in
- a **risk class** (below), which caps how much autonomy the action can ever get
- `eligible(ctx, params)`: may this customer do this right now? (e.g. you cannot drop a package
  you do not hold)
- `execute(ctx, params) -> Outcome`: what happens after approval. Either a real state change,
  a **navigation** to the normal screen with a pre-fill (the customer finishes there), or an
  **advisor hand-off**.

Adding a KBC function = adding one file under `backend/app/skills/packs/` and registering it.
No change to the core, the chat, the engine or the API.

### 2.2 Risk classes cap autonomy

| Risk | Examples | Max autonomy | Executed how |
|---|---|---|---|
| `info` | explain, compare, show | `auto` | nothing to execute |
| `internal_money` | move money between the customer's **own** accounts | `auto` (within a mandate) | `Bank.transfer`, server-validated |
| `external_money` | pay someone else | `prepare` | **never** executed by Kate: opens the normal transfer screen pre-filled |
| `product_change` | add/drop a card package, activate a Kate Deal, standing order, savings goal | `auto` only if free/saving money, else `prepare` | product state change |
| `regulated` | credit, investing, insurance advice | `prepare` | **advisor hand-off** with context (MiFID / credit law: a human decides) |

### 2.3 The consent ladder (per customer, per action)

| Level | Kate may… |
|---|---|
| `off` | never use this action, not even mention it. The chat does not even get it as a tool. |
| `suggest` | mention it and explain it ("Waarom zie ik dit?"), no pre-filled proposal |
| `prepare` | create a pre-filled **proposal**; nothing happens until the customer taps *Bevestig* |
| `auto` | execute within a customer-set **mandate** (max per execution, max per month), then report it |

Each action has a default level (mostly `prepare`) and a ceiling from its risk class. The
customer can lower any action to `off`; they can raise it only up to the ceiling. `auto` on an
action that moves money always needs a mandate (free actions such as activating a Kate Deal do
not), and mandates have hard server-side ceilings (EUR 500 per execution,
EUR 1 000 per month) that no setting can exceed.

This is the demo line: *"Kate mag van mij elke maand tot € 200 naar mijn spaarrekening zetten,
maar niets anders."* The customer grants **scoped, revocable, auditable** permission — a
personal mandate — instead of an all-or-nothing assistant.

### 2.4 Proposals: one lifecycle for every channel

Whoever wants Kate to do something — a moment from the engine, the chat, voice, the UI — creates
a **proposal**: `{action, params, source, reason}`. One code path handles all of them:

```
create ──► policy check (consent + risk ceiling + eligibility + params validation)
             │ off / not eligible ──► refused (403 / 409), nothing stored
             │ suggest            ──► stored as "suggested" (card without a button)
             │ prepare            ──► "pending"  ──approve──► execute ──► "executed" | "failed"
             │                                    └─decline──► "declined"   (24h ─► "expired")
             │ auto + in mandate  ──► execute immediately ──► "executed" (+ activity entry)
             └ auto + over mandate──► falls back to "pending"
```

- **Re-checked at approval** (consent may have changed, balance may have dropped): no
  time-of-check/time-of-use gap.
- **Idempotent:** a proposal executes at most once (status transition under a lock).
- **Owner-scoped:** every store is keyed by `owner_id`; another customer's proposal id → `404`,
  same as accounts.
- **Explainable:** `reason` is required. A proposal without a "why" is rejected.

### 2.5 Activity log: "Wat heeft Kate voor mij gedaan?"

Append-only, per customer: every proposal created, approved, declined, executed, and every
consent change, with source and reason. This is the trust screen's backbone and the audit trail
an AI Act / GDPR review would ask for.

## 3. How the other pieces plug in

### 3.1 Moments Engine → recommendations

The engine emits moments; skills turn a moment into a **concrete, pre-filled action**. The
mapping lives on the skills side (`skills/moments.py`) and is data, keyed by the moment types in
`docs/design/moments-engine.md`. `draft_for_moment(moment_type, meta)` needs only the moment
type and its `meta` strings, not the engine's code, so both can be built in parallel. The engine
passes the result to `propose(source="moment", reason=<its evidence>)`.

| Moment (engine) | Action (skill) | Params from |
|---|---|---|
| `savings_habit_automatable` | `payments.standing_order` (own savings) | `meta.amount`, `meta.day_of_month` (capped at 28) |
| `first_salary` | `savings.create_goal` | salary amount |
| `idle_savings` | `investing.prepare_meeting` (regulated → advisor) | – |
| `cashflow_risk` | `savings.move_to_current` | `meta.obligation - meta.balance` |
| `income_missing` | `advisor.book_call` | `meta.counterparty`, `meta.days_overdue` |
| `card_package_gap` | `cards.add_package` (Reispakket) | – |
| `card_package_waste` | `cards.drop_package` (Luxepakket) | – |
| `deal_match` | `deals.activate` | `meta.category` (spending category → deal: transport → fuel, leisure → dining) |
| `moving_house` | `insurance.home_quote` (regulated → advisor) | – |

So a Kate recommendation = **moment** (engine: why now, how sure) + **action** (skill: what
exactly) + **consent** (this layer: may Kate?).

### 3.2 Chat and voice → tools

`SkillsService.tools_for(owner_id)` returns only the actions this customer allows (level ≥
`suggest`), as JSON-schema tool definitions built from the params models. The chat owner swaps
the hard-coded action union for these tools and posts the model's choice to the proposal
service. A prompt-injected transaction text can at most produce a *proposal* the customer must
still confirm — and never for an action they switched off.

### 3.3 Existing chat proposals (PR #12) and subscriptions (PR #14)

PR #12 lets the chat return a `transfer` / `advisor_handoff` action that pre-fills the transfer
screen. There must be **one** proposal system, not two: after #12 is merged, a small follow-up
PR (agreed with its owner) makes the chat post its action to `SkillsService.propose(source="chat")`
and use `tools_for(owner_id)` instead of the hard-coded union. `payments.transfer` and
`advisor.book_call` already produce the same outcomes (`navigate` with the same pre-fill URL,
`advisor_handoff` with a summary), so the UI flow stays the same.

PR #14's subscription manager fits as a pack the same way (`subscriptions.remind_to_cancel`),
without changing its detection code.

### 3.4 UI

The UI needs no knowledge of individual products: it renders proposals (title, reason, params
summary, *Bevestig* / *Nee, bedankt*), the consent ladder per skill, and the activity log.

## 4. Starter packs

Enough to make the platform real in the demo, while showing that regulated domains fit too.

| Skill | Actions | Risk |
|---|---|---|
| `payments` | `transfer` (pre-fill only), `standing_order` | external_money, product_change |
| `savings` | `move_to_savings`, `move_to_current`, `create_goal` | internal_money ×2, product_change |
| `cards` | `add_package`, `drop_package` | product_change |
| `deals` | `activate` | product_change (free → may be `auto`) |
| `insurance` | `home_quote`, `travel_quote` | regulated |
| `loans` | `explore` | regulated |
| `investing` | `prepare_meeting` | regulated |
| `advisor` | `book_call` | info (hand-off, always allowed) |

Product facts (package prices: Shopping € 1,50, Reis € 7,00, Luxe € 25,00 per month) as verified
in `moments-engine.md` §11. The engine's planned `catalog.py` and the cards pack must share one
source of truth; whichever lands second imports the other.

## 5. API (additive)

| Endpoint | What |
|---|---|
| `GET /api/v1/skills` | catalogue: skills → actions, each with risk, current level, ceiling, mandate |
| `PUT /api/v1/skills/consent/{action_id}` | `{level, mandate?: {max_per_execution, max_per_month}}` |
| `POST /api/v1/proposals` | `{action, params, source, reason}` → proposal (201), `403` if not allowed, `409` if not eligible, `422` bad params |
| `GET /api/v1/proposals?status=` | the customer's proposals, newest first |
| `POST /api/v1/proposals/{id}/approve` | execute; returns the proposal with its `outcome` |
| `POST /api/v1/proposals/{id}/decline` | |
| `GET /api/v1/activity` | the append-only activity log |

Conventions as in `docs/api.md`: money is a 2-decimal string, session cookie auth, `404` = not
found *or not yours*.

## 6. Scale

- **Registry is static** (built at import); policy evaluation is a pure O(1) function, no
  model or network call: it runs for 2.3M customers for free.
- **Stores are protocols** keyed by `owner_id` (in memory now, like `Bank`; Firestore / Cloud
  SQL later, shardable by customer).
- **One authorization point** for every channel: adding voice, push or an advisor tool adds a
  *caller*, not a new policy.
- **Adding a KBC function** is one pack file; the chat's tool list, the UI's consent screen and
  the activity log pick it up automatically.

## 7. Security (Aikido: business logic, IDOR, authz)

- Every endpoint uses `CurrentUser`; stores take `owner_id`; foreign ids → `404`.
- Params validated with pydantic at create **and** at approve; unknown action → `404`.
- Risk ceilings are enforced server-side; the client cannot request `auto` for
  `external_money` or `regulated`.
- Mandates have hard ceilings; `auto` never pays a third party.
- Internal moves only target the customer's own accounts (looked up via `Bank.accounts_for`).
- Proposals expire after 24h; execution is idempotent.
- No free text from a proposal is ever executed; `reason` and `source` are displayed as text.

## 8. Testing

TDD, pytest. Unit tests on the policy (ladder × risk ceilings × mandates), the proposal
lifecycle (approve, decline, expire, double approve, re-check at approval), each pack's
`eligible`/`execute`, the moment mapping; API tests for owner scoping (`404` on another
customer's proposal), `403` on consent `off`, and the auto-within-mandate path.

## 9. Out of scope

No recommender logic of our own (that is the engine's job), no frontend, no changes to the chat
code (only the adapter it can call), no persistence beyond memory, no scheduler for standing
orders (the time machine can run them later).

## 10. Try it

`cd backend && python scripts/skills_tour.py` (optionally `--persona jan`) runs the whole flow in-process, no server or keys needed: catalogue, feed cards with a confirm button, confirming one, a mandate, the guardrails, switching an action off, and the activity log.
