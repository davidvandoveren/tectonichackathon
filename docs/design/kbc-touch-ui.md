# UI spec – KBC Touch / KBC Mobile look

Measured from the real KBC Touch "Betalen" dashboard (web) on 30/09/2026 so our PoC feels like the real environment. Only styling was captured, no customer data. We do **not** ship KBC logo files or the proprietary MuseoSans font; we use a text wordmark and a system-font fallback.

## Tokens

| Token | Value | Used for |
|---|---|---|
| `--kbc-navy` | `#0D2A50` (rgb 13,42,80) | Headings, account names, amounts |
| `--kbc-slate` | `#45658F` (rgb 69,101,143) | Secondary text: IBAN, nav labels, sub-nav |
| `--kbc-blue` | `#0097DB` (rgb 0,151,219) | Primary button, active nav, links, icons |
| `--kbc-line` | `#BFDAFF` (rgb 191,218,255) | Sidebar border, header divider, outlined tiles, segmented toggle |
| `--kbc-green` | `#7CC242` | "+ Nieuw" add icons |
| `--kbc-red` / `--kbc-red-bg` | `#D64040` / `#FFF6F5` | Warning stamps ("In overschrijding") |
| Background | `#FFFFFF` | Page, sidebar, tiles |
| Font | `"Museo Sans", system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif` | Everything, weight 500 default |

## Typography

| Element | Size / weight / color |
|---|---|
| Page title ("Betalen") | 30px / 700 / navy |
| Section title ("Zichtrekeningen") | 18px / 700 / navy |
| Header context title ("Overzicht Betalen") | 16px / 500 / navy |
| Account name | 16px / 500 / navy, uppercase |
| IBAN | 12px / 300 / slate |
| Amount | integer part 18px / 500 navy, decimals + currency 12px (`13 023,97 EUR`) |
| Sidebar label / sub-nav link | 12px / 500 / slate (active: blue) |
| Stamp | 10px / 500 / red on red-bg, radius 4px |

## Components

- **Primary button:** pill, height 40, radius 20, padding 0 24px, blue fill, white text, optional leading icon (⇄ for "Overschrijving").
- **Secondary button:** same shape, 1px blue border, blue text, transparent ("Check je gesprek").
- **Account tile:** white, radius 8, padding 12, shadow `0 2px 8px rgba(0,0,0,.16)`, ~275×110. Top-left 44px rounded square wallet icon on a light-blue gradient; name + IBAN next to it; blue ⇄ icon button top-right (starts a transfer from this account); amount bottom-right. Optional stamp centered on the top edge.
- **Empty/add tile:** 1px `--kbc-line` border, radius 4, line icon + slate text.
- **Section header:** H3 + green circled "+" and "Nieuw" link.
- **View toggle (grid/list):** segmented control, 1px `--kbc-line` border, two icon buttons, active one tinted.

## Layout

**Desktop (≥ 900px):**
- Left sidebar, 81px wide, white, `border-right: 1px solid --kbc-line`. Wordmark on top, then vertical nav items (outline icon above 12px label), active item blue with a 2px blue bar on the right edge.
- Top header across the content: context title left; right side the secondary pill button, icon buttons with small labels (Acties, Berichten, Contact) with red notification dots, and a user menu (name + chevron). 1px `--kbc-line` divider below.
- Sub-nav row of icon + 12px links under the header.
- Content left-aligned with generous left margin (~150px), max width ~1150px: title row (page title left; view toggle + primary button right), then sections with tile grids (3 columns).

**Mobile (< 900px, KBC Mobile app):** same tokens; compact top bar with wordmark and icons, full-width stacked tiles, bottom tab bar with outline icons + 12px labels, active in blue.

**Layout toggle:** small segmented control ("Mobiel / Desktop / Auto") so we can switch during demos. "Mobiel" on a wide screen renders the app inside a centered phone frame (390×844).
