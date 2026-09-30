# Kate 2.0 – alle features en hoe je ze checkt

Eén overzicht voor team en jury: wat er gebouwd is, wie het bouwde, waar je het ziet en hoe je
het in een minuut nakijkt. Alleen wat op `main` staat; open PR's staan apart onder
[In review](#in-review-nog-niet-op-main). Details van elke endpoint: [api.md](api.md).

## Zo kom je binnen

- **Live:** <https://tectonichackathon-578474883491.europe-west1.run.app>. De live versie is de
  laatste deploy en kan iets achterlopen op `main`.
- **Inloggen:** op `/login` staat één knop per persona (demo-login zonder wachtwoord,
  `PASSWORDLESS_LOGIN=true`). Alle data is synthetisch en zit in het geheugen: een herstart zet
  alles terug.
- **Lokaal:** zie [README](../README.md#how-to-run). Zet `PASSWORDLESS_LOGIN=true` en
  `ADMIN_USERNAMES=jan` in `.env` voor de demo-login en de admin-features.
- **Wie wie is:** Sander = SanderDP · Alexandre (Chun) = PeachSlayer123 · David = davidvandoveren.

### Personas

| Login | Wie | Waarvoor gebruik je die |
|---|---|---|
| `emma` | Studente, 21, Leuven, net afgestudeerd | Eerste loon, dubbele streaming (Netflix + Disney+), "Stuur Lucas 25 euro", trouwpotje |
| `jan` | Bediende, 34, Gent, verhuist binnenkort | Verhuizen, prijsstijging Netflix, tijdmachine (loon blijft uit), vader van Noor |
| `marie` | Gepensioneerd, 67, Namen | Spaargeld dat stilstaat, grootmoeder die bijdraagt aan Emma's potje |
| `sofie` | Projectingenieur, 29, Antwerpen, pendelt met de auto | Spaargewoonte automatiseren, ongebruikt Luxepakket, tankdeal: de *Bevestig*-demo |
| `bram` | Magazijnier via interim, 26, Mechelen, krap bij kas | Huur in gevaar (push, urgentie 91) en bewuste stilte (deal ingehouden) |
| `els` | Lerares, 54, Hasselt, moeder overleed onlangs | Erfenis-begeleidingsmodus in de chat, **lege** feed (geen verkoop) |
| `lucas` | Verpleegkundige, 23, Leuven, verloofd met Emma | Familiekring (partner, gedeeld potje) |
| `noor` | Scholier, 17, Gent, dochter van Jan | Familiekring (voogdij stopt op 18 jaar) |

Bron: `backend/app/domain/seed.py` (emma … els) en `backend/app/family/scenario.py` (lucas, noor).
De feeds hierboven zijn nagekeken op de live versie (30/09).

### Admin-only

De **tijdmachine** (`/demo`, `POST /api/v1/admin/time-machine`) en het **jury-dashboard**
(`/jury`, `GET /api/v1/admin/dashboard`) werken alleen voor gebruikers in `ADMIN_USERNAMES`
(`backend/app/config.py`, standaard leeg = niemand). Iedereen anders krijgt `404`, niet `403`.
Het demoscript gaat uit van `ADMIN_USERNAMES=jan`. **Op de live versie gaf dit op 30/09 voor
elke persona `404`**: zet `ADMIN_USERNAMES=jan` bij de deploy (`deploy/cloudrun.sh`) of test het
lokaal.

---

## 1. Klantervaring

| Feature | Wat het doet | Wie / PR | Waar zien (persona) | Snel checken | Status |
|---|---|---|---|---|---|
| Basis-app | Login, rekeningen, transacties, overschrijvingen met server-validatie (IBAN mod-97, max € 10.000, genoeg saldo) | David, eerste commit | `/`, `/accounts/:id`, `/transfer` (iedereen) | Doe een overschrijving naar een ongeldig IBAN: foutmelding | ✅ main |
| Demo-login met één klik | Persona-knoppen op het loginscherm, geen wachtwoord | David #11 | `/login` | `curl $URL/api/v1/auth/config` → `{"passwordless_login":true}` | ✅ main |
| KBC Touch / KBC Mobile-UI | App in KBC-stijl, wissel tussen mobiel (telefoonkader) en desktop | David #27 | Telefoon/monitor-knop in de app of op `/profile` | Klik de toggle: layout wisselt, keuze blijft bewaard | ✅ main (verfijning in #67) |
| Home "Voor jou" | Carrousel met Kate-kaarten uit het Kate-brein, met *Waarom zie ik dit?* in eigen bedragen | Alexandre #37 | `/` (emma, sofie, bram) | Open een kaart → *Waarom zie ik dit?* toont eigen cijfers | ✅ main |
| Kate-kaarten met **Bevestig** | Kate zet een actie klaar op de kaart; niets gebeurt vóór *Bevestig*. *Nee, bedankt* verbergt het moment 30 dagen | David #46 (backend #34) | `/` als **sofie**: "Elke maand op de 28e € 250 naar je spaarrekening" | Klik *Bevestig* → uitkomst op de kaart en in het activiteitenlog op `/kate` | ✅ main |
| Kate-chat ("Just say it") | Chat met Gemini (of vaste demo-antwoorden zonder key). "Stuur Lucas 25 euro voor de pizza" opent het gewone overschrijvingsscherm, al ingevuld; de klant bevestigt zelf | Sander #12, #41, #51, #57 · David #54 (Gemini-fallback) | Kate-knop in de app (**emma**) | Typ de zin → `/transfer` opent ingevuld. `GET /api/v1/kate/status` → `"llm":"gemini"` of `"mock"` | ✅ main |
| Erfenis-begeleidingsmodus | Bij overlijden/erfenis: geen marketing, stappenplan, overdracht naar adviseur met samenvatting | Sander #12 · persona Alexandre #48 | Chat als **els**: "Mijn mama is overleden, wat moet ik met de erfenis doen?" | Antwoord heeft `mode: "guidance"` en een adviseur-voorstel; feed van els is leeg | ✅ main |
| Kate-stem + spraak | Kate leest voor (ElevenLabs) en luistert (Scribe), met terugval op de browserstem. Vrouwelijke of mannelijke stem: standaard uit het klantprofiel, altijd wisselbaar | Sander #12, #20, #41 | In de chat: microfoon, luidspreker, knop *Stem van Kate* | Spreek een vraag in; wissel de stem. Lokaal: `cd backend && python -m scripts.check_kate_keys` (#33) | ✅ main |
| Abonnementen "Gebruik je dit nog?" | Vindt maandelijkse abonnementen in je eigen transacties: dubbels, prijsstijgingen, nieuw na proefperiode. Herinnering om op te zeggen, *Klopt dit niet? Verwijder* met ongedaan maken, zelf toevoegen | Sander #14, #36, #63 | `/profile` → *Mijn abonnementen* (**emma**: Netflix + Disney+; **jan**: prijsstijging Netflix) | Antwoord *Nee* op "Gebruik je dit nog?" → herinnering 3 dagen voor de volgende betaling | ✅ main |
| Familiekring | Gekoppelde accounts met wederzijdse toestemming en rechten per link (`exists`/`gift`/`pot`/`balances`), gedeeld potje, voogdij stopt op 18. Kate-suggesties met *Waarom zie ik dit?* | Sander #52 | `/profile` → *Familiekring* (**emma**: potje "Ons trouwfeest" met Lucas en Marie; **jan** ↔ **noor**) | Als **marie**: *Bevestig bijdrage* aan het trouwpotje. Uitnodiging aan een onbestaande naam geeft hetzelfde antwoord als aan een bestaande | ✅ main |
| Wat weet en mag Kate? | Eén scherm: data-toestemming (inkomen, uitgaven, saldi, producten), actie-toestemming per actie (uit / voorstellen / klaarzetten / automatisch) en *Wat heeft Kate voor mij gedaan?* | David #46 (backend Alexandre #15, David #16) | `/profile` → *Wat weet en mag Kate?* → `/kate` | Zet *uitgaven* uit als **sofie** → spaarvoorstel en deal verdwijnen van home, Luxepakket blijft | ✅ main |
| Privacy | Toestemming geldt vóór er een signaal berekend wordt; ook de chat en abonnementen respecteren ze. Eén lijst gevoelige uitgaven (gezondheid, vakbond, politiek …): nooit een moment op, in de chat als "Overige uitgave". Publieke pagina Privacy & AI | Alexandre #15, #45 · Sander #63, #55 | `/privacy` (zonder login); **jan**: vakbondslidgeld staat niet bij de abonnementen | Zet *uitgaven* uit en vraag Kate "Waar gaf ik het meest aan uit?" → ze zegt dat ze geen toegang heeft | ✅ main |

## 2. Kate-brein (Moments Engine)

Deterministische Python, geen AI-model en geen netwerk, dus goedkoop op schaal en kan niet live
falen. Vier lagen: signalen → momenten → arbitrage → compositie. Ontwerp:
[design/moments-engine.md](design/moments-engine.md). Eigenaar: Alexandre (#9, #15, #37, #45, #47, #60).

| Feature | Wat het doet | Waar zien (persona) | Snel checken | Status |
|---|---|---|---|---|
| Momenten | Signalen uit eigen transacties combineren tot momenten: `first_salary`, `income_missing`, `cashflow_risk`, `moving_house`, `idle_savings`, `savings_habit_automatable`, `deal_match`, `card_package_waste`, `card_package_gap` | `/` · emma `first_salary`, jan `moving_house`, marie `idle_savings`, sofie `savings_habit_automatable` + `card_package_waste` | `GET /api/v1/kate/feed` na inloggen | ✅ main |
| Urgentie | Score 0–100 in banden die niet overlappen: een risico wint altijd van een aanbod. Urgentiemeter op de kaart | `/` als **bram**: `cashflow_risk`, urgentie 91 | Meter op de kaart; `urgency` in de feed | ✅ main (UI #60) |
| Kanaal | Kate kiest feed, push, sms of bellen naar ernst; hoogstens één onderbreking per week. Gesimuleerde push/sms-melding in beeld | `/` als **bram** (push) | Melding "Gesimuleerde melding voor de demo" bovenaan home | ✅ main (UI #60) |
| Bewuste stilte | Wat Kate inhoudt, met reden (`cashflow_first`, `low_confidence`, `dismissed`). Een aanbod dat geld kost wacht als de buffer krap is; een besparing nooit | `/` als **bram**: blok *Bewust niet gezegd* met de supermarktdeal | `GET /api/v1/kate/feed` → `silenced[0].reason_code == "cashflow_first"` | ✅ main |
| Niet meer tonen | Een moment 30 dagen onderdrukken (een risico niet) | *Nee, bedankt* op een kaart | Kaart verdwijnt en staat onder `silenced` met `dismissed` | ✅ main |
| Tijdmachine (**admin**) | Klok van de hele app vooruit: `salary_missing`, `salary_paid` of alleen tijd. Feed, saldi en transacties blijven kloppen | `/demo` als admin (**jan**) → "+40 dagen · loon blijft uit" | Home: `income_missing`, urgentie 98, via sms. API: `POST /api/v1/admin/time-machine {"days":40,"scenario":"salary_missing"}`. Herstart de server daarna | ✅ main (UI #60) |

## 3. Kate Skills

Elke KBC-functie is een pack met acties; Kate stelt voor, de klant beslist. Ontwerp:
[design/kate-skills.md](design/kate-skills.md). Eigenaar: David (#16, #34, #38, #46, #53).
**Snelste check van alles hieronder:** `cd backend && python scripts/skills_tour.py`
(of `--persona jan` / `marie`; op Windows eerst `set PYTHONIOENCODING=utf-8` voor de €-tekens). Geen server, keys of wachtwoord nodig; het draait de echte API in-process.

| Feature | Wat het doet | Waar zien | Snel checken | Status |
|---|---|---|---|---|
| Acties (13, in 8 packs) | payments (overschrijving, doorlopende opdracht), savings (naar spaar/zicht, spaardoel), cards (pakket toevoegen/opzeggen), deals, insurance (reis/woning), loans, investing, advisor | `/kate` → sectie acties | `GET /api/v1/skills` | ✅ main |
| Toestemmingsladder | Per actie: uit → voorstellen → klaarzetten → automatisch. Geld naar een ander, krediet, beleggen en verzekeringsadvies kunnen nooit hoger dan *klaarzetten* | `/kate`, per actie | Zet `payments.transfer` op `auto` → `422` | ✅ main |
| Mandaten | *Automatisch* op een geldactie vraagt een mandaat, met harde plafonds € 500 per keer / € 1.000 per maand | `/kate` | `PUT /api/v1/skills/consent/savings.move_to_savings {"level":"auto","mandate":{"max_per_execution":"600.00","max_per_month":"800.00"}}` → `422` | ✅ main |
| Voorstellen vanuit een moment | Feed-kaart → voorstel. De server rekent het moment zelf opnieuw uit, dus de client kiest geen bedragen. Pakketten die je al betaalt tellen als bezit (#53) | `/` als **sofie** → *Bevestig* | `GET /api/v1/skills/feed-actions`, dan `POST /api/v1/proposals/from-moment {"moment":"savings_habit_automatable"}` → `201` | ✅ main |
| Activiteitenlog | *Wat heeft Kate voor mij gedaan?*, nieuwste eerst | `/kate`, onderaan | `GET /api/v1/activity` na een *Bevestig* | ✅ main |

## 4. Schaal

| Feature | Wat het doet | Wie / PR | Waar zien | Snel checken | Status |
|---|---|---|---|---|---|
| Jury-dashboard (**admin**) | Dezelfde engine (`moments.engine.run`, ongewijzigd) over een reproduceerbare synthetische populatie van 1.000 of 10.000 klanten: KPI's (o.a. % "bewust niets"), kanaalverdeling, architectuur, trace per demo-persona | Sander #30 | `/jury` als admin (niet in het menu, typ de URL) | Wissel 1.000 / 10.000. API: `GET /api/v1/admin/dashboard?size=10000` (koud ± 10 s, daarna gecachet) | ✅ main |
| Benchmark | Blok *Zo schaalt het* op `/jury`: gemeten tijd per klant (p50/gemiddeld) en omgerekend naar alle KBC-klanten. Geen LLM in dit pad; het dure AI-deel draait alleen als iemand met Kate praat | Sander #30 | `/jury` | Lees de cijfers af op de opnamedag (demoscript #64 mat p50 ± 1,3 ms) | ✅ main |

## 5. Security

Volledige kaart met tests per control: [security-and-compliance.md](security-and-compliance.md).
Basis: David (eerste commit, #10). Hardening voor Aikido: Sander #55.

| Control | Wat | Snel checken |
|---|---|---|
| Auth | Server-side sessies (alleen hash bewaard, geroteerd bij login, ingetrokken bij logout) in een `__Host-` HttpOnly SameSite=Strict-cookie; scrypt; login-rate-limit per gebruiker én per echt client-IP (vervalste `X-Forwarded-For` telt niet) | `curl $URL/api/v1/me` zonder cookie → `401` |
| Owner-scoping | Elke query neemt de id van de ingelogde klant; andermans id = dezelfde `404` als een onbestaande | Als emma: `GET /api/v1/accounts/a_jan_1` → `404` |
| Admin-gate | Admin-endpoints `404` tenzij in `ADMIN_USERNAMES` | Als emma: `GET /api/v1/admin/dashboard` → `404` |
| CSRF | SameSite=Strict + alleen JSON + Origin-check op elke wijziging | `POST` met `Content-Type: text/plain` → `415`; vreemde `Origin` → `403` |
| Rate limits | Login (5 fouten / 5 min → `429`); Kate 20 verzoeken per minuut per klant (`429`) | 6× fout wachtwoord → `429` |
| Body limits | Max 64 KB per request (chat 1 MB, spraak 3 MB) → `413` | Stuur 100 KB naar `/api/v1/transfers` → `413` |
| Headers | Strikte CSP, HSTS, `frame-ancestors 'none'`, geen API-docs in productie, `/.well-known/security.txt` | `curl -I $URL/health` |
| AI-veiligheid | Kate stelt alleen voor; transactieteksten gaan als data naar het model, modeloutput wordt tegen een schema gevalideerd | `backend/tests/test_kate.py::test_prompt_injection_*` |
| Aikido | Baseline-scan vóór en eind-scan na #55, met screenshots voor de inzending (Alexandre) | Screenshots in de Builderbase-inzending |

CI: ruff, mypy (strict), pytest, ESLint, tsc, vitest, `pip-audit`, `npm audit`, Docker build.

## 6. Tools en documenten

| Wat | Wie / PR | Gebruik |
|---|---|---|
| `backend/scripts/skills_tour.py` | David #38 | `cd backend && python scripts/skills_tour.py [--persona jan]` |
| `backend/scripts/check_kate_keys.py` | Sander #33 | `cd backend && python -m scripts.check_kate_keys` (schrijft twee stemvoorbeelden als mp3) |
| Deploy met Gemini/ElevenLabs-keys via Secret Manager | Sander #52, #62 | `deploy/cloudrun.sh` |
| Inzendtekst + demoscript (< 3 min) | Alexandre #50 | [submission.md](submission.md), [demo-script.md](demo-script.md) |

## In review (nog niet op main)

| PR | Wie | Wat |
|---|---|---|
| #64 | Alexandre | Demoscript: bewijzen dat Kate op gedrag reageert (Sofie zet geld terug → spaarvoorstel verdwijnt), fixes na de generale repetitie |
| #67 | David | Mobiel: echte KBC Mobile-layout, vaste footer, iPhone-verhoudingen |

---

## 5-minuten check voor de jury

1. [ ] Open de [live app](https://tectonichackathon-578474883491.europe-west1.run.app) en log in als **emma** (één klik).
   Home toont *Proficiat met je eerste loon!*; klik *Waarom zie ik dit?* → haar eigen bedragen.
2. [ ] Open Kate en typ **"Stuur Lucas 25 euro voor de pizza"** → het overschrijvingsscherm staat al ingevuld; niets is betaald.
3. [ ] Log in als **bram** → *Let op je saldo* via push (urgentie 91) en onder *Bewust niet gezegd* de ingehouden deal (`cashflow_first`).
4. [ ] Log in als **sofie** → kaart *Automatisch sparen* → **Bevestig** → kijk op `/kate` onder *Wat heeft Kate voor mij gedaan?*.
5. [ ] Op `/kate` als sofie: zet *uitgaven* uit → terug naar home: spaarvoorstel en deal zijn weg.
6. [ ] Log in als **els** → feed is leeg; vraag Kate *"Mijn mama is overleden, wat moet ik met de erfenis doen?"* → stappenplan + adviseur, geen verkoop.
7. [ ] Als **emma**: `/profile` → *Mijn abonnementen* (Netflix + Disney+) en *Familiekring* (potje "Ons trouwfeest").
8. [ ] Admin (**jan**, als `ADMIN_USERNAMES=jan`): `/demo` → "+40 dagen · loon blijft uit" → home: `income_missing` via sms, urgentie 98. Daarna `/jury` voor 10.000 klanten.
9. [ ] Security: `/privacy` (zonder login), en als emma `GET /api/v1/accounts/a_jan_1` → `404`.
10. [ ] Zonder browser: `cd backend && python scripts/skills_tour.py` toont alle Skills end-to-end.
