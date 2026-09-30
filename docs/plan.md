# Actieplan – Kate 2.0 (Sander · David · Chun)

Doel van dit document: **iedereen weet wat hij doet, in welke bestanden, en wie niet aan welk bestand zit.** Pas het gerust aan, maar zeg het in de teamchat.

## 1. Waar staan we (30/09)

| Wat | Status | Door |
|---|---|---|
| Repo, CI, Dependabot, CONTRIBUTING, ONBOARDING | ✅ klaar | David |
| Backend FastAPI: login (sessies, rate limit), rekeningen, transacties, overschrijvingen, "Voor jou"-insights met *Waarom zie ik dit?* | ✅ klaar, veilig opgezet | David |
| Synthetische data: 3 personas (Emma, Jan, Marie), 90 dagen, in memory | ✅ basis | David |
| Frontend React/Vite/TS in KBC Mobile-stijl: login, home + insight-carrousel, rekeningdetail, overschrijven, profiel | ✅ klaar | David |
| Docker + Cloud Run deploy | ✅ klaar | David |
| Richting: Kate als proactieve gids (David) + Kate 2.0-brein uit briefing + Family circle (Sander) | ✅ in `docs/ideas.md` | allen |
| Kate-brein (situatie, urgentie, kanaal, guardrails), tijdmachine, chat/LLM, stem, dashboard, abonnementen | ⏳ nog niets | – |
| Aikido baseline-scan | ⏳ nog niet gedaan | – |

## 2. Wat we echt laten werken (scope)

Werkende demo boven breedte. We kiezen **één demo-verhaal** dat de twee demoscripts samenvoegt:

| Prio | Onderdeel | Waarom |
|---|---|---|
| **MUST** | **Tijdmachine + urgency meter**: "spoel 1 week vooruit" → loon blijft uit / eerste loon → Kate reageert via juist kanaal (feed → push → sms), en toont ook wanneer ze bewust *niets* stuurt | Kern van de case (juiste moment, juiste kanaal), hét demomoment |
| **MUST** | **Twee personas naast elkaar**, zelfde app, andere Kate (toon + acties) | Toont personalisatie in 5 seconden |
| **MUST** | **Kate-chat** ("Just say it") met Gemini: vragen beantwoorden, overschrijving vooraf invullen, **erfenis-begeleidingsmodus** met overdracht naar adviseur | Originaliteit + fit, mens-in-de-lus |
| **MUST** | **Abonnementenbeheer**: dubbele/duurder geworden abonnementen, "Gebruik je dit nog?" | Makkelijk, concreet, spaart geld |
| **MUST** | **Jury-dashboard**: signaal → situatie → actie → reden + cijfers over 10.000 synthetische klanten | Beantwoordt "hoe schaalt dit" |
| SHOULD | Toestemmingsscherm ("Wat weet Kate over mij?") met schakelaars per signaal/kanaal | Trust = verkoopargument |
| SHOULD | Kate's stem (ElevenLabs), eventueel "AI-belt-je" bij hoogste urgentie | Wow-factor in video |
| COULD | **Family circle** (gekoppelde accounts): in de demo als 1 gedeeld potje of enkel als visie-slide | Sterk idee, maar veel autorisatiewerk |
| WON'T (vandaag) | Echt beleggingsadvies, Financial Twin, echte database | Te veel risico/tijd |

## 3. Taakverdeling

### 3.0 Werkelijke verdeling (stand 30/09, ±22:00) – dit geldt

De oorspronkelijke verdeling hieronder (3.1) is ingehaald door wat er echt gebouwd is. **Deze tabel is de waarheid**; pas hem aan zodra je iets oppakt.

| Onderdeel | Eigenaar | Code | Status |
|---|---|---|---|
| Basis-app: login, rekeningen, overschrijvingen, security, CI, Cloud Run | David | `backend/app/{routers,security,domain}/`, `Dockerfile`, `.github/` | ✅ op `main`, live |
| UI in KBC Touch/KBC Mobile-stijl + mobiel/desktop-toggle | David · **Claude-sessie UI** (#18) | `frontend/**` (behalve `kate/`, `subscriptions/`) | ✅ #27 op `main` (Cloud Run-uitrol wordt nagekeken) |
| Kate-chat (Gemini/mock), stem (ElevenLabs), erfenis-modus | Sander | `backend/app/kate/`, `routers/kate.py`, `frontend/src/kate/` | ✅ #12 op `main` |
| Abonnementenbeheer ("Gebruik je dit nog?") | Sander | `backend/app/subscriptions/`, `routers/subscriptions.py`, `frontend/src/subscriptions/` | ✅ #14 op `main` |
| Kate-brein: momenten, urgentie, kanaal, bewuste stilte, tijdmachine, data-toestemming (`PUT /kate/consent`) | Alexandre | `backend/app/moments/`, `routers/admin.py`, `routers/kate_feed.py` | ✅ #15 op `main` |
| Kate Skills: acties per KBC-functie, toestemmingsladder, mandaten, voorstellen, activiteitenlog | David · **Claude-sessie Skills** (#19) | `backend/app/skills/`, `routers/skills.py` | ✅ #16 op `main` |
| Feed-kaart → *Bevestigen*: `GET /skills/feed-actions`, `POST /proposals/from-moment` (server rekent het moment zelf opnieuw uit) | David · **Claude-sessie Skills** (#19) | `backend/app/skills/`, `routers/skills.py` | 🔍 PR #34 |
| Kate-stem vrouw/man (standaard uit klantprofiel, altijd wisselbaar) | Sander | `backend/app/kate/`, `frontend/src/kate/` | ✅ #20 op `main` |
| README "Our solution" | Alexandre | `README.md` | 🚧 `feature/readme-our-solution` |
| Nieuwe personas in `seed.py` (o.a. Sofie) – nodig voor `savings_habit_automatable` en `deal_match` | Alexandre · **Claude-sessie Personas** | `backend/app/domain/seed.py` (+ tests) | 🔍 PR #29, **MUST** – niet aan beginnen |
| `/insights` (home-carrousel "Voor jou") gevoed door de moments-engine: zelfde vorm + optioneel `urgency`/`channel`/`confidence`, respecteert toestemming en tijdmachine | Alexandre · **Claude-sessie Insights** (#31) | `backend/app/services/insights.py`, `backend/app/moments/`, insights-route in `routers/banking.py`, insights-sectie `docs/api.md` | 🔍 PR #37 |
| **Fix #35:** geen `deal_match` (of ander moment) op gevoelige uitgaven zoals de apotheek; openbaar vervoer is geen deal-handelaar | Alexandre · **Claude-sessie Insights** (#35) | `backend/app/moments/` (+ tests) | 🔍 PR #45 |
| Momenten `card_package_waste` + `card_package_gap` (ontwerp §5.2), prijzen uit Skills `cards`-pack (niet dupliceren) | Alexandre · **Claude-sessie Insights** (#39) | `backend/app/moments/` (+ tests), feed-sectie `docs/api.md` | 🚧 `feature/card-package-moments` – niet aan beginnen |
| Jury-dashboard (10.000 klanten) | Sander (#25) | – | 🔍 PR #30 |
| **Family circle**: gekoppelde accounts (wederzijdse toestemming, rechten per link), gedeeld potje, 18 jaar = voogdij stopt | Sander · **Claude-sessie Family** (#28) | `backend/app/family/`, `routers/family.py`, `frontend/src/family/` | ✅ eerste versie klaar (branch `claude/tectonic-hackathon-repo-setup-u4va4c`) |
| Sleutelcheck Gemini + ElevenLabs (`check_kate_keys`) | – | – | 🔍 PR #33 |
| Scherm **"Wat weet en mag Kate?"** (data-toestemming #15 + actie-toestemming #16 op één scherm), voorstelkaarten met *Bevestigen*, activiteitenscherm | David · **Claude-sessie UI** (#18) | `frontend/` | ⏳ backend klaar zodra #34 op `main` staat (kaartflow in `docs/api.md`) |
| Twee personas naast elkaar (demo) | David (frontend) | `frontend/` | ⏳ basis = telefoonkader-modus |
| Aikido baseline + eind-scan | Alexandre (zelf, in Aikido) | – | 🚧 baseline bezig |
| Builderbase-projecttekst + demoscript (< 3 min) | Alexandre · **Claude-sessie Personas** (#42) | nieuw: `docs/submission.md`, `docs/demo-script.md` | 🚧 `feature/submission-docs` – niet aan beginnen |
| Personas briefing-scenario's: **financieel krap** (`cashflow_risk` + bewuste stilte) en **erfenis** (context voor erfenis-modus) | Alexandre · **Claude-sessie Personas** (#43) | `backend/app/domain/seed.py` (+ tests) | 🔍 PR #48 (na #29) |
| Demovideo opnemen | **nog toe te wijzen** | – | ⏳ na demoscript (#42) |

**David werkt met twee Claude-sessies tegelijk; zo zijn ze afgebakend:**

| Sessie | Werkt aan | Raakt aan | Raakt NIET aan |
|---|---|---|---|
| **Claude-sessie UI** (#18) | KBC Touch/Mobile UI, toggle, daarna UI voor #15 en #16 | alleen `frontend/**` (niet `frontend/src/kate/`, `frontend/src/subscriptions/`) | backend |
| **Claude-sessie Skills** (#19) | Kate Skills-backend (#16) en de koppeling van chat/momenten aan voorstellen | alleen `backend/app/skills/**`, `routers/skills.py`, 2 regels in `main.py`, eigen sectie in `docs/api.md` | `frontend/**`, `kate/`, `moments/`, `subscriptions/` |

Nieuwe taken worden eerst als issue geclaimd (regel 0) voor een van beide sessies ze oppakt.

**Openstaande afstemming (dubbel werk vermijden):**
- `feature/subscriptions-chun` (Alexandre) bouwt abonnementen een tweede keer; #14 staat al op `main`. Niet mergen; extra's toevoegen aan `backend/app/subscriptions/`.
- Eén voorstel-systeem: de chat (#12) stuurt zijn `transfer`/`advisor_handoff` via `SkillsService.propose` (#16) zodra #16 op `main` staat.
- Eén lijst gevoelige categorieën: nu dubbel in `kate/context.py` en `subscriptions/detect.py` → samenvoegen in één gedeelde module.
- Eén bron voor kaartpakketprijzen: Skills `cards`-pack en `moments/catalog.py`.
- ✅ Alexandre = Alexandre Chun = "Chun" uit 3.1.
- **Brein → acties:** #16 `draft_for_moment()` zet elk moment uit #15 (ook `income_missing`) om in een vooraf ingevulde Skills-actie; #34 stelt dat beschikbaar voor de feed-kaarten (`/skills/feed-actions` + `/proposals/from-moment`).
- **Privacy (#35, Alexandre):** de engine maakt een `deal_match` van een vaste apotheek (gezondheid = gevoelig) en van De Lijn/NMBS. Skills biedt daar sinds #34 geen actie meer aan, maar de kaart zelf staat nog in de feed; fix hoort in `moments/`.
- **Toestemming = twee lagen, één scherm:** data (`PUT /kate/consent {domain, allowed}`, #15) en acties (`PUT /skills/consent/{action_id}`, #16). Abonnementen (#14) moeten het domein `spending` respecteren (Sander).

### 3.1 Oorspronkelijke verdeling (achterhaald, ter referentie)

Het principe: **elk persoon heeft eigen mappen/bestanden.** Zo krijgen we bijna geen merge-conflicten.

### Sander – Kate-brein (backend) + data
- **Personas uitbreiden** in `backend/app/domain/seed.py`: salaris blijft uit (financieel krap), erfenis-scenario, dubbele streaming-abonnementen, jong koppel. Emma/Jan/Marie blijven werken.
- **Kate-brein** in een nieuwe map `backend/app/kate/`:
  - `signals.py` – signalen uit transacties (hergebruikt `CustomerSignals` uit `services/insights.py`)
  - `situation.py` – levensfase + wat speelt er nu
  - `actions.py` – next-best-action met **urgentiescore + kanaalkeuze**, inclusief "bewust niets"
  - `guardrails.py` – gevoelige categorieën → "overige", toestemming per kanaal, mens-in-de-lus
  - `subscriptions.py` – terugkerende betalingen, dubbels, prijsstijgingen
- **Tijdmachine** + **admin-rol**: `backend/app/routers/admin.py` (alleen admin-gebruiker; injecteert transacties, schuift "vandaag" op).
- **10.000-klanten-simulatie** voor het dashboard: `backend/app/kate/population.py` (enkel regels, geen LLM → goedkoop).
- Tests in `backend/tests/test_kate_*.py`.

### David – Frontend (alles in `frontend/`)
- Kate-kaartjes met **urgentie-badge en kanaal** (uitbreiding `InsightCard`), plus "Kate stuurde bewust niets"-staat.
- **Tijdmachine-knop** (alleen zichtbaar voor admin) en **telefoon-notificaties/sms-simulatie** in beeld.
- Pagina's: **Abonnementen**, **Toestemmingen**, **Jury-dashboard** (`/admin/dashboard`), **Kate-chatpaneel** (icoon rechtsboven).
- **Twee-personas-naast-elkaar** weergave voor de demo (bv. twee telefoonframes).
- "Concept/prototype"-label, geen KBC-logo's.
- Blijft owner van `frontend/src/api/types.ts` en `App.tsx` (routes).

### Chun – Kate-chat (LLM) + stem + oplevering
- **Kate-chat endpoint** `backend/app/routers/kate_chat.py` + `backend/app/kate/llm.py`: Gemini Flash via Vertex AI, tools = bestaande owner-scoped functies (saldo, uitgaven, overschrijving *voorstellen*, nooit uitvoeren).
- **Prompt-injection-veilig**: transactieteksten en chat als data, test met "negeer je instructies…"; **rate limiting** op dit endpoint.
- **Erfenis-begeleidingsmodus**: stappenplan + adviseur-overdracht (samenvatting voor adviseur), geen marketing.
- AI-transparantie: "Ik ben Kate, een AI-assistent" bij de start.
- **Stem (ElevenLabs)**: tekst → spraak voor Kate's antwoord (stretch: "Kate belt").
- **Oplevering**: Aikido baseline-scan **nu al** (screenshot "vóór"), eind-scan (screenshot "na"), README "Our solution" invullen, projectbeschrijving voor Builderbase, demovideo < 3 min.

> Kent Chun geen Python/LLM? Dan wisselen: Chun doet dashboard + abonnementenpagina in de frontend (en oplevering), David neemt de Kate-chat. Beslis dit in de eerste 10 minuten.

## 4. Afspraken om niet in elkaars weg te zitten

**Regel 0 – eerst claimen, dan bouwen.** Voor je aan iets nieuws begint: maak een GitHub-issue `🚧 In progress (<naam>): <onderdeel>` (zoals #13) **en** zet jezelf in tabel 3.0. Staat er al iemand? Dan eerst overleggen. Zo bouwen we niets twee keer.

**Bestandseigenaarschap**

| Bestand / map | Eigenaar | Anderen |
|---|---|---|
| `backend/app/kate/**`, `backend/app/subscriptions/**`, `frontend/src/kate/`, `frontend/src/subscriptions/` | Sander | niet aanpassen, vragen |
| `backend/app/moments/**`, `routers/admin.py`, `routers/kate_feed.py`, `domain/seed.py`, `services/insights.py` | Alexandre | niet aanpassen, vragen |
| `backend/app/skills/**`, `routers/skills.py` | David | niet aanpassen, vragen |
| `frontend/**` (rest) | David | niet aanpassen, vragen |
| `backend/app/main.py` (routers registreren), `domain/models.py`, `schemas.py` | gedeeld | **alleen toevoegen, niets wijzigen**; meld het in de chat |
| `security/*`, `domain/bank.py` | David (bestaand) | *importeren* mag, herschrijven niet |
| `docs/api.md` | gedeeld | eerst contract afspreken, dan bouwen |
| `README.md` | Chun (eindverantwoordelijke) | anderen sturen tekst door |
| `docs/ideas.md` | iedereen | – |

**Werkwijze**
1. **Eerst het API-contract** (sectie 5) samen vastleggen in `docs/api.md` (15 min). Daarna kan David met nepdata bouwen terwijl Sander en Chun de endpoints maken.
2. Eén branch per taak (`feature/kate-brain`, `feature/kate-chat`, `feature/kate-ui`…), **kleine PR's**, `main` is beschermd. Review binnen 15 min: wie een PR opent, tagt de ander in de chat.
3. **Elk uur `git pull origin main`** in je branch, zodat conflicten klein blijven.
4. Security-regels voor iedereen: elke endpoint gebruikt `CurrentUser` en haalt data op via `owner_id`; admin-endpoints checken de admin-rol; nooit secrets in code (`.env`).
5. Voor je een PR opent: dezelfde checks als CI draaien (zie README).

## 5. Voorstel API-contract (nieuw, af te spreken)

> Achterhaald qua namen/eigenaars: **`docs/api.md` is de bron van waarheid** (Kate: `/kate/chat`, `/kate/speech`, `/kate/transcribe`; abonnementen: `/subscriptions`; feed/tijdmachine: #15; skills/toestemming/voorstellen: #16).

| Endpoint | Wie | Wat |
|---|---|---|
| `GET /api/v1/kate/feed` | Sander | Kate-acties voor de ingelogde klant: `{id, title, body, urgency (0–100), channel ("feed"\|"push"\|"sms"\|"call"\|"none"), reason, cta_label, cta_target, requires_advisor}` + `silenced: [{reason}]` (wat Kate bewust niet stuurde) |
| `GET /api/v1/subscriptions` | Sander | `{name, amount, frequency, price_change, duplicate_of, sensitive: false}`; gevoelige worden weggelaten |
| `POST /api/v1/subscriptions/{id}/feedback` | Sander | `{still_used: true \| false, remind_to_cancel: bool}` |
| `GET/PUT /api/v1/consent` | Sander | schakelaars per signaaltype en kanaal |
| `POST /api/v1/admin/time-machine` | Sander | admin only: `{days: 7}` → injecteert transacties, geeft nieuwe Kate-acties terug |
| `GET /api/v1/admin/dashboard` | Sander | admin only: per persona signaal→situatie→actie→reden + verdeling over 10.000 klanten |
| `POST /api/v1/kate/chat` | Chun | `{message}` → `{reply, suggested_action?, handoff_to_advisor?}`; rate-limited |
| `POST /api/v1/kate/voice` | Chun | tekst → audio (ElevenLabs), rate-limited |

## 6. Tijdlijn

| Blok | Sander | David | Chun |
|---|---|---|---|
| **Start (30 min)** | contract in `docs/api.md` + nieuwe personas | contract mee afspreken, UI-schetsen | Aikido baseline-scan + screenshot, Vertex AI + ElevenLabs keys in `.env` |
| **Sprint 1** | `kate/` situatie + urgentie + kanaal + `/kate/feed` | Kate-kaartjes met urgentie/kanaal, chatpaneel (op nepdata) | `/kate/chat` met Gemini + tools + injection-test |
| **Sprint 2** | tijdmachine + admin-rol + abonnementen | tijdmachine-knop, notificatie-simulatie, abonnementenpagina | erfenis-modus + adviseur-overdracht, stem |
| **Sprint 3** | 10k-populatie + `/admin/dashboard`, consent | dashboard + consent-scherm + 2-personas-weergave | README, Builderbase-tekst, demoscript |
| **Feature freeze** (±2 u voor deadline) | Aikido-fixes | Aikido-fixes, polish | Aikido eind-scan + screenshot, **video opnemen** |
| **Submit** | – | – | finale submit (daarna niets meer wijzigen!) |

## 7. Direct te beslissen (eerste 10 minuten, samen)

- [ ] Klopt de rolverdeling? (vooral: kan Chun de LLM-kant aan, anders wisselen met David)
- [ ] Family circle: echte feature (1 gedeeld potje) of enkel visie-slide?
- [ ] Demo lokaal opnemen of via Cloud Run?
- [ ] Kate alleen in het Nederlands, of ook FR/EN?
- [ ] Hoe laat is de feature freeze precies?
