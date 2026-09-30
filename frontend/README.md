# KBC Mobile PoC – frontend

Vite + React 19 + TypeScript (strict) web client for the KBC personalization
proof of concept, styled to match KBC Touch (desktop) and KBC Mobile (phone) —
see `docs/design/kbc-touch-ui.md` for the measured design spec. No UI kit, no
CSS framework: plain CSS with design tokens (`src/styles/tokens.css`) and
per-component CSS modules. No external fonts/CDNs — the font stack falls back
to system fonts (compatible with the backend's `default-src 'self'` CSP).

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
                formatting/summing/splitting, never floats), dates.ts (nl-BE formatting,
                transaction grouping), cta.ts (safe-internal-path check for insight CTAs)
  auth/         AuthContext/AuthProvider (calls /me once, exposes the user via
                context), RequireAuth (route guard, redirects to /login)
  layout/       the mobile/desktop layout system — see "Layout modes" below
  kate/         AskKateButton, the "Vraag het Kate" entry point (currently an
                inert placeholder; wire its `onClick` to open the Kate chat
                surface once it exists)
  components/   reusable UI: Button, TextField, SelectField, Skeleton, ErrorState,
                EmptyState, AccountCard, AccountSection, SectionHeader,
                EmptyAccountTile, TileViewToggle, MenuLink, TransactionList,
                TabBar, AppLayout, PageHeader, Wordmark, InsightCard,
                InsightCarousel, icons/ (hand-written inline SVGs, no icon font/CDN)
  pages/        LoginPage, HomePage, AccountDetailPage, TransferPage, ProfilePage,
                NotFoundPage
  styles/       tokens.css (CSS custom properties, matching docs/design/kbc-touch-ui.md),
                global.css (reset, focus styles, reduced-motion handling)
```

## Layout modes

The app renders as either **KBC Touch** (desktop: sidebar + header, `DesktopShell`)
or **KBC Mobile** (phone: top bar + bottom tab bar, `MobileShell`), picked by
`src/layout/ViewModeProvider.tsx`:

- **`auto`** (default) resolves to desktop at viewport width ≥ 900px (via
  `matchMedia`, live-updated on resize) and mobile below it.
- **`mobile`** / **`desktop`** force a layout regardless of viewport. Forcing
  `mobile` on a wide viewport renders `MobileShell` inside a centered
  390×844 `PhoneFrame` — useful for demos/recordings.

The choice is persisted to `localStorage["ui.viewMode"]`
(`src/layout/viewModeStorage.ts`); every read/write is wrapped in try/catch
and falls back to `"auto"` if storage is unavailable (it's a UI preference
only, never personal data — the only localStorage use in this app).

A small segmented control, `<ViewModeToggle>` (`role="radiogroup"`, arrow-key
navigable), lets you switch modes: floating bottom-right on desktop and as a
compact floating button on mobile, plus inline on the profile page and the
login page.

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
  client never reads or stores a token. The only `localStorage` use anywhere
  in `src/` is the mobile/desktop layout preference (see "Layout modes"
  above) — a UI setting, never personal or session data, and every
  read/write is wrapped in try/catch.
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
- The Betalen (home) page follows the KBC Touch layout, which doesn't show a
  combined total balance — accounts are grouped into sections by type
  instead. `src/lib/money.ts` still exports a tested, `BigInt`-based
  `sumMoney` (integer cents, never float math) for future use.
- IBAN validation implements the general ISO 13616 mod-97 checksum (5–34
  alphanumeric characters), not a Belgium-specific length/format check,
  since the contract only specifies "must pass the mod-97 checksum".
