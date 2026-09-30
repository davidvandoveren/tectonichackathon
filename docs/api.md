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
[{"id": "i_…", "kind": "moment", "title": "Eerste loon ontvangen?", "body": "…", "cta_label": "Start met sparen", "cta_target": "/transfer", "reason": "We zagen een nieuwe maandelijkse storting van je werkgever."}]
```
`reason` is the plain-language "Waarom zie ik dit?" explanation and is **always** present. Today these come from simple rules in `backend/app/services/insights.py`; this is where the PoC's personalization engine plugs in.

### Kate (chat, voice, speech recognition)
All Kate endpoints need a login and share a per-customer rate limit (`KATE_MAX_REQUESTS_PER_MINUTE`, default 20 → `429`). Upstream failures (Gemini/ElevenLabs) → `503`. Without keys Kate runs in **demo mode** (`llm: "mock"`, canned answers) and the UI falls back to the browser's own speech recognition and voice.

`GET /api/v1/kate/status` → `{"llm": "mock" | "gemini", "voice": true, "speech_recognition": true}`

`POST /api/v1/kate/chat` body `{"message": "Stuur Lucas 25 euro voor de pizza", "history": [{"role": "kate" | "user", "text": "…"}]}` (message ≤ 1000 chars, history ≤ 10 turns) →
```json
{"reply": "…", "mode": "normal" | "guidance",
 "action": {"type": "none" | "transfer" | "advisor_handoff", "to_name": "Lucas", "amount": "25.00", "description": "Pizza", "summary": null}}
```
A `transfer` action is only a **proposal**: the UI opens `/transfer?to_name=…&amount=…&description=…` and the customer confirms on the normal, server-validated transfer screen. `guidance` mode (bereavement, inheritance, …) means: no marketing, step plan, `advisor_handoff` with a summary for the advisor. Kate only ever sees the logged-in customer's own data (no IBANs; sensitive spending shown as "Overige uitgave"); transaction texts are passed to the model as data, never as instructions.

`POST /api/v1/kate/speech` body `{"text": "…"}` → `audio/mpeg` (ElevenLabs voice).

`POST /api/v1/kate/transcribe` body `{"audio_base64": "…", "mime_type": "audio/webm"}` (≤ 2 MB; webm/ogg/mp4/mpeg/wav) → `{"text": "…"}` (ElevenLabs Scribe).

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
