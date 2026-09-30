# API contract (v1)

Base path: `/api/v1`. JSON only. Served same-origin with the web app, so no CORS.

## Conventions
- **Money** is always a decimal **string** with 2 decimals (`"1234.50"`, `"-12.99"`), never a float. Currency is ISO 4217 (`"EUR"`).
- **Dates** are ISO 8601 (`"2026-09-28"` for dates, `"2026-09-28T14:03:00Z"` for timestamps).
- **Auth**: `POST /auth/login` sets an `HttpOnly`, `SameSite=Strict` session cookie. The browser sends it automatically (`fetch(..., { credentials: "same-origin" })`). The frontend never sees or stores a token.
- **Errors**: `{"detail": "<message>"}` with a proper status code. `401` = not logged in, `404` = not found *or not yours* (we never reveal that another user's resource exists), `422` = validation error, `429` = too many attempts.
- State-changing requests must send `Content-Type: application/json` (CSRF defence together with SameSite=Strict).

## Endpoints

### Health
`GET /health` → `{"status": "ok"}` (no `/api/v1` prefix; not `/healthz`, which Cloud Run reserves)

### Auth
`GET /api/v1/auth/demo-users` → the synthetic personas you can log in as (for the login screen)
```json
[{"username": "emma", "display_name": "Emma Peeters", "persona": "Student, 21, Leuven"}]
```

`POST /api/v1/auth/login` body `{"username": "emma", "password": "..."}` → `200` + session cookie, body = `Me` (below). Wrong credentials → `401 {"detail": "Invalid username or password"}`.

`GET /api/v1/auth/config` → `{"passwordless_login": false}`

`POST /api/v1/auth/demo-login` body `{"username": "emma"}` → `200` + session cookie, body = `Me`. One-click demo login without password; only when the server runs with `PASSWORDLESS_LOGIN=true`, otherwise `404`.

`POST /api/v1/auth/logout` → `204`, cookie cleared.

### Me
`GET /api/v1/me` →
```json
{"id": "u_emma", "username": "emma", "first_name": "Emma", "last_name": "Peeters", "persona": "Student, 21, Leuven"}
```

### Accounts
`GET /api/v1/accounts` →
```json
[{"id": "a_emma_1", "name": "Zichtrekening", "type": "current", "iban": "BE68 5390 0754 7034", "balance": "1234.50", "currency": "EUR"}]
```
`type` is one of `current`, `savings`, `credit_card`.

`GET /api/v1/accounts/{account_id}` → one `Account` (404 if not yours).

`GET /api/v1/accounts/{account_id}/transactions?limit=50` (limit 1–200, newest first) →
```json
[{"id": "t_…", "account_id": "a_emma_1", "booked_at": "2026-09-28", "description": "Colruyt Leuven", "counterparty": "Colruyt", "amount": "-42.17", "currency": "EUR", "category": "groceries"}]
```
`category` is one of `income`, `groceries`, `housing`, `transport`, `leisure`, `shopping`, `utilities`, `savings`, `transfer`, `other`.

### Transfers
`POST /api/v1/transfers`
```json
{"from_account_id": "a_emma_1", "to_iban": "BE71096123456769", "to_name": "Lucas Janssens", "amount": "25.00", "description": "Pizza"}
```
Rules: amount `> 0`, max 2 decimals, ≤ 10000.00, ≤ available balance; IBAN must pass the mod-97 checksum (spaces allowed); `to_name` 1–70 chars; `description` 0–140 chars. Returns `201` with the created `Transaction` (negative amount on the source account).

### Insights ("Voor jou") – the personalization hook
`GET /api/v1/insights` →
```json
[{"id": "i_first_salary_u_emma", "kind": "moment", "title": "Proficiat met je eerste loon!", "body": "…", "cta_label": "Start met sparen", "cta_target": "/transfer", "reason": "We zagen een nieuwe maandelijkse storting van je werkgever.",
  "moment": "first_salary", "urgency": 39, "channel": "feed", "confidence": 0.82}]
```
`reason` is the plain-language "Waarom zie ik dit?" explanation and is **always** present.

Fed by the moments engine (see [Kate feed](#kate-feed-the-moments-engine)): home shows exactly the items of `GET /kate/feed`, in the same order (highest urgency first), and obeys the same consent switches, dismissals and time machine. What Kate deliberately keeps quiet about is only in the feed's `silenced`.

- `kind`: `alert` (a risk, e.g. a missing salary), `guidance` (needs an advisor), otherwise `moment`.
- `moment` is the moment type: pass it to `POST /kate/feed/{moment}/dismiss` for "Niet meer tonen".
- `urgency` (0–100), `channel` and `confidence` (0–1) are **optional additions**; the original fields keep their meaning, so older clients keep working.

### Kate (chat, voice, speech recognition)
All Kate endpoints need a login and share a per-customer rate limit (`KATE_MAX_REQUESTS_PER_MINUTE`, default 20 → `429`). Upstream failures (Gemini/ElevenLabs) → `503`. Without keys Kate runs in **demo mode** (`llm: "mock"`, canned answers) and the UI falls back to the browser's own speech recognition and voice.

**Data consent:** Kate's chat only receives the kinds of data the customer allowed via `PUT /api/v1/kate/consent` (`spending` → spend + outgoing transactions, `income` → incoming, `balances` → balances, `products` → accounts). What is switched off is listed to the model as `withheld`, and Kate says she has no access instead of guessing. Sensitive spending is defined once in `backend/app/privacy/sensitive.py`.

`GET /api/v1/kate/status` → `{"llm": "mock" | "gemini", "voice": true, "speech_recognition": true}`

`POST /api/v1/kate/chat` body `{"message": "Stuur Lucas 25 euro voor de pizza", "history": [{"role": "kate" | "user", "text": "…"}]}` → Kate reads the first 1000 chars of `message`, the last 10 history turns and the first 1200 chars of each turn. Anything longer is trimmed, not refused (`truncated: true` says the question was cut). Only absurd input is refused with `422`: message > 8000 chars, > 100 turns, or a turn > 8000 chars. A blank message is also refused. →
```json
{"reply": "…", "mode": "normal" | "guidance",
 "action": {"type": "none" | "transfer" | "advisor_handoff", "to_name": "Lucas", "amount": "25.00", "description": "Pizza", "summary": null},
 "truncated": false}
```
Kate says she is an AI in her first reply only (a conversation whose history has no `kate` turn). `guidance` starts with empathy and a question (action `none`); the `advisor_handoff` follows once the customer accepts help.
**One proposal system:** every `transfer` / `advisor_handoff` from the chat is also a Kate Skills proposal (`payments.transfer` / `advisor.book_call`, `source: "chat"`), returned as `action.proposal_id` + `action.proposal_status`. `pending` → the card shows *Bevestigen* (`POST /api/v1/proposals/{id}/approve`) / *Nee, dank je* (`…/decline`); `suggested` → the customer finishes it themselves; action switched `off` → no card and Kate says so. It shows up in `GET /api/v1/activity`.

A `transfer` action is only a **proposal**: the UI opens `/transfer?to_name=…&amount=…&description=…` and the customer confirms on the normal, server-validated transfer screen. `guidance` mode (bereavement, inheritance, …) means: no marketing, step plan, `advisor_handoff` with a summary for the advisor. Kate only ever sees the logged-in customer's own data (no IBANs; sensitive spending shown as "Overige uitgave"); transaction texts are passed to the model as data, never as instructions.

`POST /api/v1/kate/speech` body `{"text": "…"}` → `audio/mpeg` in the customer's chosen voice (ElevenLabs).

`GET /api/v1/kate/voice` → `{"voice": "female" | "male", "default_voice": "female", "available": ["female", "male"]}`. Two voices; the **default follows the gender registered on the customer record** (never guessed from a name), unknown → Kate's default (female). `available` lists the voices configured in ElevenLabs (empty = browser voice fallback).

`POST /api/v1/kate/voice` body `{"voice": "male"}` → the same shape; the customer's own choice always wins.

`POST /api/v1/kate/transcribe` body `{"audio_base64": "…", "mime_type": "audio/webm"}` (≤ 2 MB; webm/ogg/mp4/mpeg/wav) → `{"text": "…"}` (ElevenLabs Scribe).
## Kate feed (the moments engine)

Design: [`docs/design/moments-engine.md`](design/moments-engine.md). The proactive half of Kate
is fully deterministic — no model, no network call — so it cannot fail during a demo.

`GET /api/v1/kate/feed` →
```json
{
  "items": [
    {
      "id": "first_salary",
      "title": "Proficiat met je eerste loon!",
      "body": "Zet elke maand automatisch een klein deel opzij...",
      "urgency": 39,
      "channel": "feed",
      "reason": "Op 25/09 kwam er € 1 985,00 binnen van Proximus NV, een betaler die we niet eerder zagen. ...",
      "cta_label": "Start met sparen",
      "cta_target": "/transfer",
      "requires_advisor": false
    }
  ],
  "silenced": [
    {"moment": "deal_match", "reason_code": "cashflow_first", "reason": "Je saldo staat krap. ..."}
  ]
}
```

- `id` is the moment type, stable across requests, and is what you pass to the dismiss endpoint.
  Moment types: `cashflow_risk`, `income_missing` (risk) · `moving_house` (obligation) · `first_salary`, `idle_savings`, `savings_habit_automatable`, `deal_match`, `card_package_waste` (pays for Reis-/Luxepakket, no travel seen → drop it and save), `card_package_gap` (travels, no Reispakket) (opportunity).
- `urgency` is `0–100`. Bands do not overlap: `risk` 70–100, `obligation` 40–69, `opportunity` 10–39, so a risk can never be outranked by a confident nudge. Items come back ranked, highest first.
- `channel` is one of `feed`, `push`, `sms`, `call`, `none`. **At most one item per response uses an interruptive channel** (`push`/`sms`/`call`); the rest fall back to `feed`.
- `reason` is the "Waarom zie ik dit?" text. It is assembled from the evidence that produced the moment, so it can never drift from what was actually observed. Always present, never empty.
- `silenced` is what Kate found and deliberately did **not** say. `reason_code` is one of `low_confidence`, `cashflow_first`, `dismissed`. Worth showing in the UI — it is the most distinctive part of the engine.

`POST /api/v1/kate/feed/{moment_type}/dismiss` → `204`. Suppresses that moment for 30 days; it then appears under `silenced` with `reason_code: "dismissed"`. A `risk` moment is never suppressed this way. Send `{}` as the body — the CSRF guard requires `Content-Type: application/json`.

### Consent ("Wat weet Kate over mij?")

`GET /api/v1/kate/consent` → `{"income": true, "spending": true, "balances": true, "products": true}`

`PUT /api/v1/kate/consent` body `{"domain": "spending", "allowed": false}` → the updated object. An unknown domain gives `422`.

`products` covers what Kate reads about the customer's KBC products (card packages); switching it off silences `card_package_waste` and lets `card_package_gap` fire without knowing a package is held.

Consent is applied **before** signal extraction, so a domain the customer switched off is never computed rather than computed and filtered. Switching off `spending` visibly changes the feed.

### Time machine (demo only, admin only)

`POST /api/v1/admin/time-machine` body `{"days": 40, "scenario": "salary_missing", "username": "jan"}` →
```json
{"days_shifted": 40, "clock_offset_days": 40, "today": "2026-11-09",
 "username": "jan", "injected": 0, "feed": {"items": [...], "silenced": [...]}}
```

`scenario` is one of:

| Scenario | What happens |
|---|---|
| `none` | Only the clock moves. |
| `salary_paid` | The persona's own recurring income is projected into the window, derived from their transaction history (not from the seed file), and balances move with it. |
| `salary_missing` | The projection is skipped, so money the customer counts on never arrives. The engine notices and escalates off the feed. **This is the demo.** |

`days` is `1–365`; `username` defaults to the calling admin. Moving the clock shifts `get_today` for the *whole* app, so balances, transactions and the feed stay coherent.

Requires the caller's username to be listed in `ADMIN_USERNAMES`. Anyone else — including a logged-in customer — gets **`404`, not `403`**: a caller who may not use an endpoint does not get to learn that it exists.


### Subscriptions ("Gebruik je dit nog?")
`GET /api/v1/subscriptions` → monthly subscriptions detected in the customer's **own** transactions:
```json
{"subscriptions": [{"id": "sub_3f2a…", "name": "Netflix", "group": "streaming", "amount": "13.49", "previous_amount": null,
  "yearly_cost": "161.88", "frequency": "monthly", "first_seen": "2026-07-28", "last_charged": "2026-09-26",
  "next_expected": "2026-10-26", "flags": ["duplicate"], "duplicate_of": ["Disney+"], "reason": "We zien sinds …",
  "status": "unknown" | "in_use" | "cancel_reminder", "remind_on": null}],
 "monthly_total": "36.47", "yearly_total": "437.64", "yearly_savings": "0.00", "hidden_sensitive": 0}
```
`flags`: `price_increase`, `duplicate` (two services in the same `group`), `trial_converted`. The bank does not know *usage*, so we never guess it; the customer answers. Sensitive subscriptions (health, religion, politics, trade union, dating) are only counted in `hidden_sensitive`, never shown or analysed.

Detection is **automatic**; the customer never has to enter anything. Recently detected ones have `is_new: true` (UI: "Nieuw gedetecteerd · Klopt dit niet? Verwijder").

`POST /api/v1/subscriptions/{id}/dismiss` body `{"dismissed": true}` → removes it from the list with one click (the overview is returned; `dismissed` counts them). `{"dismissed": false}` undoes it. `404` if not yours.

`POST /api/v1/subscriptions` body `{"name": "Streamz", "amount": "9.99", "next_charge": "2026-10-15"}` (`next_charge` optional) → `201` + overview. Optional manual add, e.g. for a subscription paid with another bank's card (`source: "manual"`).

With the `spending` consent switched off, nothing is detected: `subscriptions` only holds what the customer added manually and `spending_consent` is `false` (the page explains why and links to `/kate`).

`POST /api/v1/subscriptions/{id}/feedback` body `{"still_used": false, "remind_to_cancel": true}` → the updated subscription (`status: "cancel_reminder"`, `remind_on` = 3 days before the next charge). `404` if the id is not one of *your* subscriptions.

### Kate Skills – what Kate can do, and may do (see `docs/design/kate-skills.md`)
Every KBC function (payments, savings, cards, deals, insurance, loans, investing, advisor) registers **actions**. Each customer sets a consent **level** per action: `off` (Kate never uses it, not even in chat) · `suggest` (mention only) · `prepare` (pre-filled proposal, customer confirms) · `auto` (executes within a **mandate**). The server caps the level per action (`max_level`): paying someone else and anything regulated (credit, investing, insurance advice) is at most `prepare`. POSTs without a body still need `Content-Type: application/json` (send `{}`).

`GET /api/v1/skills` →
```json
[{"id": "savings", "title": "Sparen", "description": "…",
  "actions": [{"id": "savings.move_to_savings", "title": "Geld opzij zetten", "description": "…",
               "risk": "internal_money", "level": "prepare", "max_level": "auto", "mandate": null}]}]
```
`risk` is one of `info`, `internal_money`, `external_money`, `product_change`, `regulated`.

`PUT /api/v1/skills/consent/{action_id}` body `{"level": "auto", "mandate": {"max_per_execution": "50.00", "max_per_month": "200.00"}}` → the updated action (shape above). `auto` on a money action needs a mandate; hard ceilings € 500 per execution / € 1 000 per month. Above `max_level` or over a ceiling → `422`; unknown action → `404`.

`POST /api/v1/proposals` body `{"action": "savings.move_to_savings", "params": {"amount": "50.00"}, "source": "moment" | "chat" | "voice" | "ui", "reason": "Waarom zie ik dit?-tekst"}` → `201`
```json
{"id": "p_…", "action": "savings.move_to_savings", "params": {"amount": "50.00"},
 "summary": "€ 50,00 naar je spaarrekening", "source": "moment", "reason": "…",
 "status": "pending", "created_at": "2026-09-30T18:40:00Z", "outcome": null}
```
`status`: `suggested` (level `suggest`: show as a card without a confirm button) · `pending` (show *Bevestig* / *Nee, bedankt*) · `executed` (also returned straight away when `auto` + within mandate) · `failed` · `declined` · `expired` (after 24h). Consent `off` → `403`; not possible for this customer right now (e.g. not enough balance, package already held) → `409` with a plain-Dutch `detail`; bad params → `422`. The params per action are in the action's `description`, and as JSON schema via the chat tools.

`GET /api/v1/proposals?status=pending` → the customer's proposals, newest first.

`POST /api/v1/proposals/{id}/approve` body `{}` → the proposal with `status: "executed"` and an `outcome`:
```json
{"kind": "done" | "navigate" | "advisor_handoff", "message": "…", "navigate_to": "/transfer?to_name=Lucas&amount=25.00&description=Pizza", "handoff_summary": null}
```
`navigate` = open that screen pre-filled; the customer finishes there (Kate never pays a third party). `advisor_handoff` = show the message; `handoff_summary` is what the advisor receives. Consent lowered meanwhile → `403`; no longer possible or not pending → `409`; not yours → `404`.

`POST /api/v1/proposals/{id}/decline` body `{}` → the proposal with `status: "declined"`.

`GET /api/v1/activity` → "Wat heeft Kate voor mij gedaan?", newest first:
```json
[{"at": "2026-09-30T18:40:00Z", "event": "proposed" | "suggested" | "executed" | "failed" | "declined" | "expired" | "consent_changed",
  "action": "savings.move_to_savings", "summary": "€ 50,00 naar je spaarrekening", "source": "moment", "reason": "…"}]
```

#### Feed cards → confirmable actions
`GET /api/v1/skills/feed-actions` → for each card in `GET /kate/feed` that Kate can act on (join on feed `id` == `moment`):
```json
[{"moment": "first_salary", "action": "savings.create_goal", "title": "Spaardoel maken",
  "summary": "Spaardoel 'Buffer' van € 5 955,00", "level": "prepare", "can_confirm": true}]
```
No entry = no button on that card (no matching action, the customer switched the action `off`, or it is not possible right now). `can_confirm: false` = level `suggest`: show the summary, no button. Cards at sensitive merchants (health, religion, politics, trade union) never get an action.

`POST /api/v1/proposals/from-moment` body `{"moment": "first_salary"}` → `201` proposal (same shape as `POST /proposals`, `source: "moment"`, `reason` = the engine's evidence). The server recomputes the moment itself, so a client cannot choose the amounts; a moment that is not in this customer's feed right now → `404`; consent `off` → `403`; not possible → `409`; extra fields → `422`.

Card flow: **Bevestig** → `POST /proposals/from-moment` → `POST /proposals/{id}/approve` `{}` → show `outcome.message` (`navigate`: open `outcome.navigate_to`; `advisor_handoff`: show that an advisor will call). **Nee, bedankt** → `POST /kate/feed/{moment}/dismiss` `{}`.

### Family circle – linked accounts (`/family`)
Customers link their accounts to the people around them. A link exists only after **both** sides accept; each side chooses what **it** shares with the other and can never raise what the other shares. Either side can end a link at any time. Levels, each including the previous: `exists` (only that the link exists) · `gift` (may contribute to pots you share with them, sees progress only) · `pot` (also sees who gave what) · `balances` (also your account balances, read-only; never transactions or IBANs).

**Minors:** guardianship comes from the civil registry (seeded: Jan → Noor), never from an invite. Until the 18th birthday the guardian sees the child's balances by law and neither side can end the link (`409`). On the birthday (the app clock, so the time machine shows it) it ends automatically and only the child's own choice counts. Minors cannot be invited, cannot invite and get no nudges to give money.

`GET /api/v1/family` →
```json
{"me": {"minor": false, "adult_on": null},
 "links": [{"id": "fl_3f2a9c1b7d4e", "status": "active" | "pending", "direction": null | "incoming" | "outgoing",
   "other_name": "Lucas Janssens", "my_role": "partner", "their_role": "partner", "i_share": "pot", "they_share": "pot",
   "guardianship": null | {"my_side": "guardian" | "ward", "active": true, "ends_on": "2026-10-21"},
   "can_end": true, "can_view_accounts": false, "since": "2026-07-02"}],
 "pots": [{"id": "fp_…", "name": "Ons trouwfeest", "goal": "8000.00", "balance": "2500.00", "progress_percent": 31,
   "owner_name": "Emma Peeters", "mine": true, "access": "owner" | "pot" | "gift", "members": ["Lucas Janssens"] | null,
   "contributions": [{"name": "Lucas Janssens", "amount": "150.00", "booked_on": "2026-09-28", "mine": false}]}],
 "suggestions": [{"id": "…", "kind": "invite" | "guardianship_ending" | "now_adult" | "pot_contribution",
   "title": "…", "body": "…", "reason": "Waarom zie ik dit?", "cta_label": "…", "cta_target": "/family"}]}
```
Roles: `partner`, `parent`, `child`, `grandparent`, `grandchild`, `godparent`, `godchild`, `sibling`, `other`.

`POST /api/v1/family/invites` body `{"username": "lucas", "my_role": "partner", "share": "exists"}` → `202 {"message": "…", "link": Link}`. **Same answer whether or not the username is a customer** (or a minor, or already linked): an outgoing invite only ever shows what you typed. Max 10 open invites.

`POST /api/v1/family/links/{id}/accept` body `{"share": "gift"}` → `Link` (only the invitee; `409` if already answered).
`POST /api/v1/family/links/{id}/sharing` body `{"share": "pot"}` → `Link` (changes only *your* side).
`POST /api/v1/family/links/{id}/end` body `{}` → `204` (decline, cancel or end; `409` during guardianship).
`GET /api/v1/family/links/{id}/accounts` → `[{"name": "Spaarrekening", "type": "savings", "balance": "1150.00", "currency": "EUR"}]`, only if the other side shares `balances` with you.
`POST /api/v1/family/pots` body `{"name": "Huis", "goal": "20000.00", "member_link_ids": ["fl_…"]}` → `201 Pot` (members = your own active links; a member sees the pot only while you share at least `gift` with them).
`POST /api/v1/family/pots/{id}/contributions` body `{"from_account_id": "a_marie_1", "amount": "50.00", "note": "Van oma"}` → `201 Pot`. Uses the normal transfer rules (own account, no credit card, enough funds, max € 10.000).

Every endpoint answers **`404` for "unknown" and "not yours" alike** (another customer's link or pot, an account that is not yours), so nothing can be enumerated. Demo logins added for this: `lucas` (Emma's fiancé) and `noor` (Jan's daughter, 17, turns 18 in three weeks).

### Jury dashboard (admin only)
`GET /api/v1/admin/dashboard?size=10000` (`size` 100–10 000) → Kate's real engine (`moments.engine.run`, unchanged) run over a reproducible synthetic population, plus a trace per demo persona. Same `AdminUser` gate as the time machine: `404` for everyone else, off unless `ADMIN_USERNAMES` is set. Follows the time machine's clock. Cached per (size, day); a cold 10 000 run takes ~10 s.
```json
{"today": "2026-09-30",
 "population": {"size": 10000, "with_message": 5470, "interrupted": 1053, "silent": 4530, "nothing_at_all": 4257, "held_back": 273,
   "by_moment": {"deal_match": 2312, "idle_savings": 1439}, "by_channel": {"feed": 5018, "push": 635, "sms": 163, "call": 255},
   "silence_reasons": {"low_confidence": 414}, "silence_labels": {"low_confidence": "…"},
   "archetypes": [{"archetype": "salary_missing", "label": "Loon blijft uit", "customers": 308, "with_message": 308, "interrupted": 308, "silent": 0, "top_moments": ["income_missing"]}],
   "p50_ms": 0.73, "p95_ms": 1.17, "p99_ms": 1.6, "kbc_customers": 2300000, "full_bank_cpu_minutes": 28.1},
 "personas": [{"username": "jan", "display_name": "Jan Maes", "persona": "…", "signals": [{"type": "…", "evidence": "…"}],
   "moments": [{"type": "moving_house", "urgency": "obligation", "confidence": "0.60"}],
   "actions": [{"title": "Ga je verhuizen?", "channel": "feed", "urgency": "57", "reason": "…"}], "silenced": []}]}
```
UI: `/jury` (full width, outside the phone frame).

