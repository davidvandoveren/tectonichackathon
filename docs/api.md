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
