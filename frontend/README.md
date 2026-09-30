# KBC Mobile PoC – frontend

Vite + React 19 + TypeScript (strict) mobile-web client for the KBC Mobile
personalization proof of concept. No UI kit, no CSS framework: plain CSS with
design tokens (`src/styles/tokens.css`) and per-component CSS modules.

Not a real bank. Synthetic demo data only, served by the FastAPI backend in
`../backend`.

## Scripts

```bash
npm install
npm run dev        # Vite dev server, proxies /api and /health to http://localhost:8000
npm run build       # tsc -b && vite build -> dist/
npm run preview     # preview the production build
npm run lint         # eslint .
npm run typecheck   # tsc -b
npm test            # vitest run
```

Run the backend separately on `:8000`; `vite.config.ts` proxies `/api` and
`/health` there in dev. In production the backend serves `frontend/dist`
from the same origin, so there is no CORS and no API base URL to configure.

## Structure

```
src/
  api/          typed fetch client (client.ts), request/response types (types.ts),
                one file per resource (auth.ts, me.ts, accounts.ts, transfers.ts, insights.ts)
  lib/          iban.ts (mod-97 validation + formatting), money.ts (decimal-string
                formatting/summing, never floats), dates.ts (nl-BE formatting,
                transaction grouping), cta.ts (safe-internal-path check for insight CTAs)
  auth/         AuthContext/AuthProvider (calls /me once, exposes the user via
                context), RequireAuth (route guard, redirects to /login)
  components/   reusable UI: Button, TextField, SelectField, Skeleton, ErrorState,
                EmptyState, AccountCard, TransactionList, TabBar, AppLayout,
                PageHeader, Wordmark, InsightCard, InsightCarousel, icons/ (hand-written
                inline SVGs, no icon font/CDN)
  pages/        LoginPage, HomePage, AccountDetailPage, TransferPage, ProfilePage,
                NotFoundPage
  styles/       tokens.css (CSS custom properties), global.css (reset, focus
                styles, reduced-motion handling)
```

## Where the personalization slot lives

`src/components/InsightCard.tsx` is the "Voor jou" card: title, body, an
optional CTA (only rendered when `cta_target` is a safe internal path, see
`src/lib/cta.ts`), and an expandable "Waarom zie ik dit?" toggle that reveals
the `reason` text from `GET /api/v1/insights`. `src/components/InsightCarousel.tsx`
renders the horizontally scrollable row of these cards, and is mounted at the
top of `src/pages/HomePage.tsx`. This is the one component a personalization
engine needs to feed (i.e. the backend's `/insights` response) to change what
shows up here.

## Security notes

- Session is an HttpOnly, `SameSite=Strict` cookie set by the backend; the
  client never reads or stores a token (no localStorage/sessionStorage use
  anywhere in `src/`).
- `src/api/client.ts` always sends `credentials: "same-origin"`, adds
  `Content-Type: application/json` on writes, and broadcasts a global event
  on any `401` (`onUnauthorized`), which `AuthProvider` uses to clear auth
  state; `RequireAuth` then redirects to `/login`.
- No `dangerouslySetInnerHTML`, no inline scripts/handlers, no external
  fonts/CDNs/icon libraries — compatible with a strict
  `default-src 'self'` CSP applied by the backend.
- Transfer form validates client-side (IBAN mod-97, amount bounds/decimals,
  name/description lengths) but always treats the server's 401/404/422/429
  response as the source of truth and surfaces its `detail` message.

## Assumptions / open questions for the API contract

- The demo personas (`GET /auth/demo-users`) don't include a password; the
  login form collects whatever the user types and sends it to
  `POST /auth/login` as-is. The backend/demo data decides what's valid.
- `Insight.kind` is typed as `string` (only `"moment"` appears as an example
  in the contract, not as an exhaustive enum).
- The transfer confirmation screen assumes the `Transaction` returned by
  `POST /transfers` has `counterparty` set to the submitted `to_name` (used
  on the success screen).
- Total balance on the home screen sums all accounts as a single figure,
  assuming a single currency (EUR) across a user's accounts — summation uses
  integer cents (`BigInt`) rather than float math to stay exact.
- IBAN validation implements the general ISO 13616 mod-97 checksum (5–34
  alphanumeric characters), not a Belgium-specific length/format check,
  since the contract only specifies "must pass the mod-97 checksum".
