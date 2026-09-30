# Demoscript – video < 3 min

Eigenaar: Alexandre (#42). Eén verhaal, zeven scènes, ± 170 s. Elke scène zegt welke persona, wat
je klikt, wat Kate doet en wat de voice-over zegt. De kolom **Status** zegt of het vandaag al werkt
op `main` of op welke PR het wacht. Werk die kolom bij tot de opname. Wat bij de opname niet werkt,
schrap je (zie *Plan B*).

**Voorbereiding**
- Draai de Cloud Run-versie of lokaal met `PASSWORDLESS_LOGIN=true` (één klik per persona) en
  `ADMIN_USERNAMES=jan` (tijdmachine).
- Zet de Gemini- en ElevenLabs-keys in `.env` en controleer ze met
  `cd backend && python -m scripts.check_kate_keys` (#33). Zonder keys werkt alles in demomodus,
  maar dan is de stem die van de browser.
- Start elke opname met een **verse server**. Alle data zit in het geheugen, en de tijdmachine
  verzet de klok voor de hele app.
- Neem de scènes apart op en monteer ze achteraf. Zo kan één fout niet de hele opname verpesten.

## Overzicht

| # | Scène | Persona | Duur | Status |
|---|---|---|---|---|
| 1 | Zelfde app, andere Kate | Emma ↔ Lucas | 20 s | ✅ via inloggen · ⏳ naast elkaar: David |
| 2 | Kate houdt zich bewust in | Lucas | 25 s | ✅ `/kate/feed` (API) · 🔍 home #37 · ⏳ stiltes zichtbaar in UI |
| 3 | Tijdmachine: het loon blijft uit | Jan | 30 s | ✅ API · ⏳ knop in UI |
| 4 | Een gewoonte automatiseren | Sofie | 20 s | 🔍 persona #29 · ✅ backend *Bevestig* · ⏳ knop op kaart |
| 5 | Just say it | Emma | 15 s | ✅ |
| 6 | Erfenis: begeleiden in plaats van verkopen | Els | 30 s | 🔍 persona #48 · ✅ chat, stem, erfenismodus |
| 7 | Zo ziet dit eruit voor 2,3 miljoen klanten | – | 25 s | 🔍 dashboard #30 |
| | Slot: vertrouwen en veiligheid | – | 10 s | ✅ tekst · ⏳ toestemmingsscherm |

---

## 1 · Zelfde app, andere Kate (20 s)

**Beeld:** Emma en Lucas naast elkaar (telefoonkaders). Anders: log eerst in als Emma, knip, en
log dan in als Lucas.
**Kate:** Emma krijgt "Proficiat met je eerste loon!". Lucas krijgt geen reclame, maar een
waarschuwing over zijn huur.
**Voice-over:**
> "KBC's Kate herkent vandaag meer dan 140 situaties. Die zijn allemaal met de hand geschreven.
> Twee klanten, dezelfde app, en toch een totaal andere Kate. Niemand heeft deze situaties
> geschreven. Kate stelt ze samen uit signalen in hun eigen transacties."

## 2 · Kate houdt zich bewust in (25 s)

**Persona:** `lucas`, met € 212 op zijn zichtrekening en € 720 huur op de 1e.
**Klik:** open de kaart en daarna *Waarom zie ik dit?*
**Kate:** `cashflow_risk` via **push**. De reden gebruikt zijn eigen bedragen. Onder "Bewust niet
gezegd" staat zijn supermarkt-deal met als reden `cashflow_first`: *"Je saldo staat krap.
Voorstellen die je geld kosten houden we daarom even voor ons."*
**Voice-over:**
> "Wie veel herkent, kan ook veel spammen. Daarom beslist Kate niet alleen wát ze zegt, maar ook
> wanneer ze moet zwijgen. Een aanbod dat geld kost, houdt ze in zolang je buffer krap is. Een
> voorstel dat je geld bespaart, houdt ze nooit in."

*Plan B:* als de stiltes nog niet in de UI staan, toon dan de persona-trace van Lucas op het
jury-dashboard (scène 7).

## 3 · Tijdmachine: het loon blijft uit (30 s)

**Persona:** `jan` (admin).
**Klik:** tijdmachine → `salary_missing` → +40 dagen. Via de API is dat
`POST /api/v1/admin/time-machine {"days": 40, "scenario": "salary_missing", "username": "jan"}`.
**Kate:** `income_missing` springt bovenaan, als `alert` met **urgentie 98**, en gaat van feed naar
**sms** (nagekeken op de seed). Toon de urgentiemeter.
**Voice-over:**
> "We spoelen veertig dagen vooruit. Jans loon blijft uit. Kate stuurt geen kaartje in de app
> maar escaleert naar het kanaal dat past bij de ernst. Dat gebeurt hoogstens één keer per week,
> zodat hij niet overspoeld wordt."

## 4 · Een gewoonte automatiseren (20 s)

**Persona:** `sofie`.
**Kate:** *"Je zette de laatste maanden zelf € 250 op je spaarrekening."* Ze stelt een
doorlopende opdracht voor met **Sofie's eigen bedrag en dag**, niet met een bedrag dat de bank
kiest.
**Klik:** **Bevestig** → klaar. Toon daarna *Wat heeft Kate voor mij gedaan?*
**Voice-over:**
> "Sofie spaart al, maar ze doet het elke maand met de hand. Kate zet dat om in een vaste
> opdracht, met haar eigen cijfers. Eén tik, en de klant blijft zelf beslissen."

## 5 · Just say it (15 s)

**Persona:** `emma`.
**Klik:** open Kate en typ of zeg *"Stuur Lucas 25 euro voor de pizza"*.
**Kate:** het gewone overschrijvingsscherm opent, al ingevuld. Emma bevestigt zelf.
**Voice-over:**
> "Eén zin in plaats van vijf schermen. Kate vult alles in, maar betaalt nooit zelf aan iemand
> anders. De klant bevestigt op het gewone, gevalideerde scherm."

## 6 · Erfenis: begeleiden in plaats van verkopen (30 s)

**Persona:** `els`. Haar mama overleed onlangs; de historiek toont de uitvaart, de notaris en de
uitkering van de nalatenschap.
**Klik:** zeg tegen Kate *"Mijn mama is overleden, wat moet ik met de erfenis doen?"*
(gesproken, met de stem).
**Kate:** schakelt naar **begeleidingsmodus**. Ze geeft een stappenplan zonder marketing en
biedt aan om een adviseur in te schakelen, met een samenvatting zodat Els haar verhaal niet
opnieuw hoeft te vertellen. Toon ook dat de feed van Els **leeg** is: geen beleggingsreclame na
een overlijden.
**Voice-over:**
> "Er is een moment waarop een bank níét moet verkopen. Kate herkent het, begeleidt Els, en
> geeft haar door aan een mens, met de volledige context."

## 7 · Zo ziet dit eruit voor 2,3 miljoen klanten (25 s)

**Beeld:** `/jury`, het jury-dashboard over 10.000 synthetische klanten.
**Toon:** de KPI **"Kregen bewust niets": 45,3 %**, de verdeling van de kanalen en de meting van
**0,73 ms per klant**. Dat is ± 28 CPU-minuten voor alle KBC-klanten, zonder AI-model.
**Voice-over:**
> "Dit is dezelfde motor, gedraaid over tienduizend klanten. Bijna de helft kreeg bewust niets,
> en dat is precies de bedoeling. Voor alle klanten van KBC is het minder dan een half uur
> rekenwerk, zonder taalmodel. Het dure AI-deel draait alleen wanneer iemand met Kate praat."

*(Controleer de cijfers na de merge van #30.)*

## Slot · Vertrouwen en veiligheid (10 s)

**Beeld:** het scherm *"Wat weet en mag Kate?"*. Zet een schakelaar uit en de feed verandert.
Toon daarna de Aikido-screenshot "na".
**Voice-over:**
> "Elke suggestie zegt waarom. Jij kiest wat Kate mag weten en wat ze mag doen. Kate 2.0: de
> juiste boodschap, op het juiste moment, via het juiste kanaal, of bewust helemaal niets."

---

## Plan B (als iets niet af is bij de opname)

| Ontbreekt | Vervang door |
|---|---|
| Twee telefoons naast elkaar | Na elkaar inloggen, met een harde knip |
| Stiltes niet zichtbaar in de UI | Persona-trace van Lucas op `/jury` |
| Tijdmachine-knop | Swagger (`/api/docs`, alleen in dev) of een `curl`, gevolgd door een refresh van home (#37) |
| *Bevestig*-knop op kaart | Scène 4 schrappen of vervangen door `python scripts/skills_tour.py --persona sofie` (#38) in een terminal |
| Jury-dashboard | De benchmarkcijfers als slide |
| API-keys werken niet | Demomodus: browserstem en vaste antwoorden. Scène 6 werkt dan nog, maar klinkt minder goed |
