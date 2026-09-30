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
