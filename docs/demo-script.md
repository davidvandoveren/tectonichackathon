# Demoscript – video < 3 min

Eigenaar: Alexandre (#42). Eén verhaal in zeven scènes, ± 170 s. Elke scène zegt welke persona,
wat je klikt, wat er op het scherm komt en wat de voice-over zegt.

De schermteksten tussen aanhalingstekens zijn **nagekeken op de echte app**. Ik heb het gerepeteerd
via de API op `main` plus #29 (Sofie) en #48 (Lucas, Els), in demomodus zonder API-keys. Wat nog
niet gebouwd is, staat in [Nog te bouwen voor de demo](#nog-te-bouwen-voor-de-demo). Voor elk
gat is er een plan B.

## Overzicht

| # | Scène | Persona | Duur | Klaar? |
|---|---|---|---|---|
| 1 | Dezelfde deal, twee antwoorden | Emma ↔ Lucas | 35 s | ✅ na elkaar · ⏳ naast elkaar, stilte zichtbaar |
| 2 | Tijdmachine: het loon blijft uit | Jan | 25 s | ✅ API · ⏳ knop, kanaal-badge |
| 3 | Kate automatiseert wat je al doet | Sofie | 25 s | ✅ na merge #29 |
| 4 | Just say it | Emma | 15 s | ✅ |
| 5 | Erfenis: begeleiden in plaats van verkopen | Els | 30 s | ✅ na merge #48 |
| 6 | Zo ziet dit eruit voor 2,3 miljoen klanten | – | 25 s | 🔍 #30 |
| 7 | Slot: jij beslist | Emma | 15 s | ✅ |

## Voorbereiding

1. Start een **verse server**. Alle data zit in het geheugen en de tijdmachine verzet de klok voor
   de hele app. Gebruik `PASSWORDLESS_LOGIN=true` (inloggen met één klik) en
   `ADMIN_USERNAMES=jan` (tijdmachine).
2. Voor de echte stem en Gemini zet je de keys in `.env` en controleer je ze met
   `cd backend && python -m scripts.check_kate_keys`. Zonder keys werkt alles ook: dan gebruikt
   Kate vaste antwoorden en de stem van de browser.
3. Zet het toestel in de **mobiele weergave** (telefoonkader) en zoom de browser op 125 %, zodat
   de tekst leesbaar is in de video.
4. Neem **elke scène apart** op en monteer achteraf. Herstart de server vóór scène 2 (de
   tijdmachine), zodat de klok daarna niet verzet blijft voor de andere scènes.

---

## 1 · Dezelfde deal, twee antwoorden (35 s)

**Beeld:** Emma links, Lucas rechts. Is "naast elkaar" niet klaar, neem dan Emma op, knip, en neem
daarna Lucas op.

**Emma** (21, eerste loon), home "Voor jou":
- de kaart "Er is een deal die bij jou past": cashback in de supermarkt, met een *Bevestig*-knop
- swipe naar "Proficiat met je eerste loon!" en open *Waarom zie ik dit?*. Kate toont de
  storting van haar nieuwe werkgever, met het echte bedrag en de echte datum.

**Lucas** (26, interim, € 212 op zijn rekening, huur € 720 op de 1e), home "Voor jou":
- één kaart, **"Let op je saldo"**, als alert via **push**, met urgentie 91
- géén deal, hoewel hij net als Emma al zijn boodschappen in één supermarkt doet. Kate hield
  die deal bewust in, met als reden: *"Je saldo staat krap. Voorstellen die je geld kosten houden
  we daarom even voor ons; eerst je rekening."*

**Voice-over:**
> "KBC's Kate herkent vandaag meer dan honderdveertig situaties, allemaal met de hand geschreven.
> Kate 2.0 stelt ze samen uit signalen in je eigen transacties. Emma en Lucas doen allebei hun
> boodschappen in één supermarkt. Emma krijgt de deal. Lucas niet: zijn huur staat op het spel,
> dus Kate waarschuwt hem en houdt de reclame bewust in. Een voorstel dat geld kost, wacht tot je
> buffer in orde is. Een voorstel dat je geld bespaart, wacht nooit."

## 2 · Tijdmachine: het loon blijft uit (25 s)

**Persona:** `jan`, admin. Zijn feed begint op "Ga je verhuizen?" (feed, urgentie 57).
**Klik:** tijdmachine → scenario `salary_missing` → **+40 dagen**. Zolang de knop er niet is, gebruik
je `POST /api/v1/admin/time-machine {"days": 40, "scenario": "salary_missing", "username": "jan"}`
(Swagger in dev) en ververs je home.
**Scherm:** bovenaan staat nu een **alert**, `income_missing`, met **urgentie 98**, en Kate kiest
**sms** in plaats van een kaartje. *Waarom zie ik dit?* toont: *"Acme Logistics BV betaalde je
elke maand, maar de storting is nu … dagen te laat."*

**Voice-over:**
> "We spoelen veertig dagen vooruit. Jans loon komt niet. Kate wacht niet tot hij de app opent,
> maar kiest het kanaal dat past bij de ernst: een sms. Hoogstens één onderbreking per week, dus
> Jan wordt niet overspoeld."

## 3 · Kate automatiseert wat je al doet (25 s)

**Persona:** `sofie` (29, Antwerpen, pendelt met de auto). Home toont drie kaarten:
1. **"Wil je dit automatisch laten doen?"**, want ze zette de laatste maanden zelf € 250 opzij.
   De actie luidt: *"Elke maand op de 28e € 250,00 naar je spaarrekening"*. Dat zijn haar eigen
   bedrag en haar eigen dag.
2. **"Betaal je voor iets dat je niet gebruikt?"**: ze betaalt € 25 per maand voor het Luxepakket
   en reist nooit.
3. **"Er is een deal die bij jou past"**: cashback voor tanken, want ze tankt elke week bij
   hetzelfde station.

**Klik:** op kaart 1 → **Bevestig**. Kate antwoordt: *"Vanaf nu gaat elke maand op de 28e € 250,00
naar je sparen."* Toon daarna kort Profiel → *Wat weet en mag Kate?* → het activiteitenlog.

**Voice-over:**
> "Sofie spaart al, maar ze doet het elke maand met de hand. Kate zet dat om in een vaste
> opdracht, met háár bedrag en háár dag. En ja: Kate stelt ook voor om minder te betalen. Een
> bank die zichzelf geld kost, dat is vertrouwen."

## 4 · Just say it (15 s)

**Persona:** `emma`.
**Klik:** open Kate en zeg of typ *"Stuur Lucas 25 euro voor de pizza"*.
**Scherm:** Kate zegt *"Ik heb een overschrijving van € 25,00 naar Lucas klaargezet. Controleer
ze en bevestig zelf."* Het gewone overschrijvingsscherm opent, al ingevuld, en Emma drukt op
**Bevestigen**.

**Voice-over:**
> "Eén zin in plaats van vijf schermen. Kate vult alles in, maar betaalt nooit zelf iemand
> anders. Jij bevestigt, op het gewone, beveiligde scherm."

## 5 · Erfenis: begeleiden in plaats van verkopen (30 s)

**Persona:** `els` (54, Hasselt). Toon eerst kort haar rekening: "Uitvaart mama", "Provisie
notaris", "Nalatenschap mama - uitkering". Toon dan home: **geen enkele kaart**. Na een
overlijden verkoopt Kate niets.
**Klik:** zeg tegen Kate (met de stem) *"Mijn mama is overleden, wat moet ik met de erfenis doen?"*
**Scherm:** Kate gaat in **begeleidingsmodus**: *"Wat verdrietig, gecondoleerd. Ik help je stap
voor stap, zonder haast: 1) de overlijdensakte, 2) een attest of akte van erfopvolging, 3) daarna
kan een adviseur de rekeningen met je overlopen. Zal ik een gesprek met een adviseur klaarzetten,
zodat je je verhaal niet opnieuw hoeft te doen?"* Daaronder staat het blok **"Menselijke adviseur"**, met
de samenvatting die de adviseur meekrijgt.

**Voice-over:**
> "Er zijn momenten waarop een bank níét moet verkopen. Na een erfenis zou elk systeem
> beleggingen voorstellen. Kate niet. Ze begeleidt Els, en geeft haar door aan een mens die alles
> al weet."

## 6 · Zo ziet dit eruit voor 2,3 miljoen klanten (25 s)

**Beeld:** `/jury`, het jury-dashboard (#30).
**Toon:** de KPI **"Kregen bewust niets"**, de verdeling van de kanalen, en de meting **"per klant
± 0,7 ms"**. Klik daarna één persona-trace open: signalen → moment → actie → reden.

**Voice-over:**
> "Dit is dezelfde motor, over tienduizend synthetische klanten. Bijna de helft kreeg bewust
> niets, en dat is precies de bedoeling. Voor alle klanten van KBC is dat minder dan een half uur
> rekenwerk, zonder taalmodel. De AI draait alleen wanneer iemand met Kate praat."

*(Controleer de percentages en de milliseconden op het dashboard zelf, na de merge van #30.)*

## 7 · Slot: jij beslist (15 s)

**Persona:** `emma` → Profiel → **"Wat weet en mag Kate?"**
**Klik:** zet de gegevens over **uitgaven** uit en ga terug naar home. De supermarkt-deal is weg.
Toon kort de ladder per actie: *Uit / Alleen tippen / Klaarzetten / Automatisch*.
**Voice-over:**
> "Elke suggestie zegt waarom. Jij kiest wat Kate mag weten, en wat ze mag doen. Kate 2.0: de
> juiste boodschap, op het juiste moment, via het juiste kanaal. Of bewust helemaal niets."

Eindbeeld: de Aikido-screenshot "na", het logo van de repo en de URL.

---

## Nog te bouwen voor de demo

Dit mist nog om het script zonder plan B op te nemen. Het staat in volgorde van belang, en de
eigenaar komt uit de tabel in `docs/plan.md`.

| Wat | Waarom nodig | Eigenaar |
|---|---|---|
| **"Bewust niet gezegd"** zichtbaar maken (`silenced` uit `GET /kate/feed`) | Kern van scène 1: nu staat de stilte alleen in de API | David (UI) |
| **Kanaal- en urgentie-badge** op de kaart (push/sms/call) | Scène 1 en 2: laat zien dat Kate van kanaal wisselt | David (UI) |
| **Tijdmachine-knop** (alleen voor admin) | Scène 2 zonder Swagger | David (UI) |
| **Twee telefoons naast elkaar** | Scène 1 in één beeld | David (UI) |
| Luxepakket in `Holdings` van Sofie, zodat kaart 2 een *Bevestig*-knop krijgt | Scène 3: nu heeft die kaart nog geen knop | David (Skills) |
| `"u_lucas": "male"` in `kate/voices.py` | Lucas krijgt nu nog de vrouwenstem | Sander |
| Jury-dashboard mergen | Scène 6 | Sander (#30) |
| Merge van #29 en #48 | Sofie, Lucas en Els bestaan pas na de merge | review |

## Plan B

| Ontbreekt bij opname | Vervang door |
|---|---|
| Twee telefoons naast elkaar | Na elkaar opnemen, met een harde knip |
| Stilte niet zichtbaar in de UI | De persona-trace van Lucas op `/jury`, of een tekst-overlay in de montage met de echte reden |
| Tijdmachine-knop | Swagger (`/api/docs`, alleen in dev), dan home verversen |
| Jury-dashboard | De benchmarkcijfers als slide |
| Keys werken niet | Demomodus: dezelfde teksten, met de stem van de browser |
