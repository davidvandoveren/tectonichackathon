# Demo – Kate 2.0 (video < 3 min)

> **Waarvoor is dit document?** Het is de enige bron voor de demovideo: wat we tonen, waarom, met
> welke persona, wat je klikt, wat er op het scherm komt en wat de voice-over zegt. Het is
> geschreven zodat iemand zonder voorkennis de video kan opnemen.
>
> Eigenaar: Alexandre (issue #42) · Laatst gerepeteerd: 30/09/2026 via de echte API op `main`, plus
> PR #29 (Sofie) en PR #48 (Lucas, Els), in demomodus zonder API-keys. Tekst tussen
> aanhalingstekens is letterlijk wat de app toont.

---

## 1. De boodschap in één zin

> **KBC's Kate herkent vandaag 140 situaties die met de hand geschreven zijn. Kate 2.0 stelt ze
> samen uit signalen, en beslist wat ze zegt, wanneer, via welk kanaal, of dat ze bewust niets
> zegt.**

Wat de jury na 3 minuten moet onthouden:

1. **Samengesteld, niet geschreven.** Kate herkent situaties uit signalen in de eigen transacties
   van de klant. Niemand heeft ze vooraf geprogrammeerd.
2. **Bewuste stilte.** Kate weet ook wanneer ze níét moet spreken, en zegt waarom.
3. **Het juiste kanaal.** Een kaartje in de app, een push, een sms of een telefoontje, afhankelijk
   van de ernst.
4. **De klant beslist.** Kate zet dingen klaar, de klant bevestigt. Na een overlijden verkoopt Kate
   niets en schakelt ze een mens in.
5. **Het schaalt.** Dezelfde motor draait over 10.000 klanten, in minder dan een milliseconde per
   klant, zonder AI-model.

### Hoe de demo scoort op de jurycriteria

| Criterium (gewicht) | Waar in de demo |
|---|---|
| Creativiteit (30 %) | Samengestelde situaties, bewuste stilte, een bank die voorstelt om minder te betalen (scène 1, 3) |
| Technisch (30 %) | Alles live in de app: tijdmachine, bevestigen, chat met stem, dashboard (scène 2–6) |
| Fit met de uitdaging (30 %) | Juiste moment en kanaal, schaal naar 2,3 miljoen klanten (scène 2, 6) |
| Security (10 %) | De klant bevestigt zelf, toestemming per gegevensdomein en per actie, Aikido-screenshot (scène 4, 7) |

---

## 2. Begrippen (voor wie de code niet kent)

| Begrip | Betekenis |
|---|---|
| **Signaal** | Een kleine vaststelling in de eigen gegevens, bijvoorbeeld "loon 5 dagen te laat" of "betaalt 13 keer bij hetzelfde tankstation". |
| **Moment** | Een combinatie van signalen met een zekerheidsscore, bijvoorbeeld "eerste loon", "verhuis" of "saldo krap". |
| **Arbitrage** | Kate beslist wat ze zegt, in welke volgorde en via welk kanaal. Een risico gaat altijd vóór een aanbod. Kate onderbreekt de klant hoogstens één keer per week. |
| **Bewuste stilte** | Iets wat Kate zag maar bewust niet zegt, met een reden. Bijvoorbeeld *cashflow_first*: geen voorstellen die geld kosten zolang je saldo krap is. |
| **Urgentie** | Een score van 0 tot 100. Risico's scoren 70–100, verplichtingen 40–69 en kansen 10–39. |
| **Kanaal** | `feed` (kaartje in de app), `push`, `sms` of `call`. |
| **Waarom zie ik dit?** | Onder elke kaart staat de uitleg, met de eigen bedragen en datums van de klant. |
| **Bevestig** | Kate zet een actie klaar en de klant bevestigt. Kate betaalt nooit zelf aan iemand anders. |
| **Tijdmachine** | Een demotool, alleen voor admins, die de klok vooruit zet, bijvoorbeeld "40 dagen verder, het loon blijft uit". |

---

## 3. De personas

Alle klanten zijn synthetisch. Je logt in met één klik op het loginscherm.

| Login | Wie | Wat Kate toont (gerepeteerd) | Scène |
|---|---|---|---|
| `emma` | 21, Leuven, net haar eerste loon | "Er is een deal die bij jou past" (supermarkt) · "Proficiat met je eerste loon!" | 1, 4, 7 |
| `lucas` | 26, Mechelen, interim, € 212 op zijn rekening, huur € 720 | "Let op je saldo" (**push**, urgentie 91). De deal wordt **bewust ingehouden** | 1 |
| `jan` | 34, Gent, gaat verhuizen (admin voor de tijdmachine) | "Ga je verhuizen?" (urgentie 57). Na de tijdmachine: loon te laat, via **sms**, urgentie 98 | 2 |
| `sofie` | 29, Antwerpen, pendelt met de auto | "Wil je dit automatisch laten doen?" · "Betaal je voor iets dat je niet gebruikt?" · "Er is een deal die bij jou past" (tanken) | 3 |
| `els` | 54, Hasselt, haar moeder overleed onlangs | **Geen enkele kaart.** In de chat: begeleidingsmodus en een adviseur | 5 |
| `marie` | 67, Namen, gepensioneerd, veel spaargeld | "Je spaargeld kan meer voor je doen" (adviseur) · deal | niet in de video |

> Sofie bestaat pas na de merge van PR #29, Lucas en Els na de merge van PR #48.

---

## 4. Het verhaal in 7 scènes (± 170 seconden)

| # | Scène | Persona | Duur | Klaar? |
|---|---|---|---|---|
| 1 | Dezelfde deal, twee antwoorden | Emma ↔ Lucas | 35 s | ✅ na elkaar · ⏳ naast elkaar, stilte zichtbaar in de UI |
| 2 | Tijdmachine: het loon blijft uit | Jan | 25 s | ✅ via API · ⏳ knop, kanaal-badge |
| 3 | Kate automatiseert wat je al doet | Sofie | 25 s | ✅ na merge #29 |
| 4 | Just say it | Emma | 15 s | ✅ |
| 5 | Erfenis: begeleiden in plaats van verkopen | Els | 30 s | ✅ na merge #48 |
| 6 | Zo ziet dit eruit voor 2,3 miljoen klanten | – | 25 s | 🔍 PR #30 |
| 7 | Slot: jij beslist | Emma | 15 s | ✅ |

---

### Scène 1 · Dezelfde deal, twee antwoorden (35 s)

**Doel:** in één beeld tonen dat Kate per klant anders beslist, en dat ze bewust kan zwijgen.

**Beeld:** Emma links, Lucas rechts. Is "naast elkaar" nog niet klaar, neem dan eerst Emma op en
daarna Lucas, met een harde knip.

**Emma**, home "Voor jou":
1. Eerste kaart: **"Er is een deal die bij jou past"**, cashback in de supermarkt, met een
   *Bevestig*-knop.
2. Swipe naar **"Proficiat met je eerste loon!"** en tik op *Waarom zie ik dit?* Kate toont de
   storting van haar nieuwe werkgever, met het echte bedrag en de echte datum.

**Lucas**, home "Voor jou":
1. Eén kaart: **"Let op je saldo"**, als alert via **push**, urgentie 91.
2. **Géén deal**, hoewel hij net als Emma al zijn boodschappen in één supermarkt doet. Kate hield
   die deal bewust in, met als reden: *"Je saldo staat krap. Voorstellen die je geld kosten houden
   we daarom even voor ons; eerst je rekening."*

**Voice-over:**
> "KBC's Kate herkent vandaag meer dan honderdveertig situaties, allemaal met de hand geschreven.
> Kate 2.0 stelt ze samen uit signalen in je eigen transacties. Emma en Lucas doen allebei hun
> boodschappen in één supermarkt. Emma krijgt de deal. Lucas niet: zijn huur staat op het spel,
> dus Kate waarschuwt hem en houdt de reclame bewust in. Een voorstel dat geld kost, wacht tot je
> buffer in orde is. Een voorstel dat je geld bespaart, wacht nooit."

---

### Scène 2 · Tijdmachine: het loon blijft uit (25 s)

**Doel:** tonen dat Kate het juiste moment en het juiste kanaal kiest.

**Persona:** `jan`, admin. Zijn home begint met **"Ga je verhuizen?"** (feed, urgentie 57).

**Klik:** tijdmachine → scenario **"loon blijft uit"** → **+40 dagen**.
Zolang de knop niet bestaat: in Swagger (`/api/docs`, alleen in dev)
`POST /api/v1/admin/time-machine` met `{"days": 40, "scenario": "salary_missing", "username": "jan"}`,
en daarna home verversen.

**Op het scherm:** bovenaan staat nu een **alert over het loon** met **urgentie 98**. Kate kiest
**sms** in plaats van een kaartje. *Waarom zie ik dit?* toont: *"Acme Logistics BV betaalde je
elke maand, maar de storting is nu … dagen te laat."*

**Voice-over:**
> "We spoelen veertig dagen vooruit. Jans loon komt niet. Kate wacht niet tot hij de app opent,
> maar kiest het kanaal dat past bij de ernst: een sms. Hoogstens één onderbreking per week, dus
> Jan wordt niet overspoeld."

---

### Scène 3 · Kate automatiseert wat je al doet (25 s)

**Doel:** tonen dat Kate werkt met de eigen cijfers van de klant, en dat ze ook voorstelt om
minder te betalen.

**Persona:** `sofie`. Home toont drie kaarten:
1. **"Wil je dit automatisch laten doen?"**, want ze zette de laatste maanden zelf € 250 opzij.
   De actie luidt: *"Elke maand op de 28e € 250,00 naar je spaarrekening"*. Dat zijn **haar eigen
   bedrag en dag**.
2. **"Betaal je voor iets dat je niet gebruikt?"**: € 25 per maand voor het Luxepakket, terwijl ze
   nooit reist.
3. **"Er is een deal die bij jou past"**: cashback voor tanken, want ze tankt elke week bij
   hetzelfde station.

**Klik:** op kaart 1 → **Bevestig**. Kate antwoordt: *"Vanaf nu gaat elke maand op de 28e € 250,00
naar je sparen."* Toon daarna kort **Profiel → "Wat weet en mag Kate?"** en het activiteitenlog
met de uitgevoerde actie.

**Voice-over:**
> "Sofie spaart al, maar ze doet het elke maand met de hand. Kate zet dat om in een vaste
> opdracht, met háár bedrag en háár dag. En ja: Kate stelt ook voor om minder te betalen. Een
> bank die zichzelf geld kost, dat is vertrouwen."

---

### Scène 4 · Just say it (15 s)

**Doel:** tonen dat één zin vijf schermen vervangt, en dat de klant altijd zelf bevestigt.

**Persona:** `emma`.

**Klik:** open Kate en zeg of typ *"Stuur Lucas 25 euro voor de pizza"*.

**Op het scherm:** Kate zegt *"Ik heb een overschrijving van € 25,00 naar Lucas klaargezet.
Controleer ze en bevestig zelf."* Het gewone overschrijvingsscherm opent, al ingevuld, en Emma
drukt op **Bevestigen**.

**Voice-over:**
> "Eén zin in plaats van vijf schermen. Kate vult alles in, maar betaalt nooit zelf iemand
> anders. Jij bevestigt, op het gewone, beveiligde scherm."

---

### Scène 5 · Erfenis: begeleiden in plaats van verkopen (30 s)

**Doel:** tonen dat Kate weet wanneer een bank níét moet verkopen, en dat ze een mens inschakelt.

**Persona:** `els`.
1. Toon kort haar rekening: *"Uitvaart mama"*, *"Provisie notaris"*, *"Nalatenschap mama -
   uitkering"*.
2. Toon home: **geen enkele kaart**. Geen beleggingsreclame na een overlijden.

**Klik:** zeg tegen Kate, met de stem: *"Mijn mama is overleden, wat moet ik met de erfenis doen?"*

**Op het scherm:** Kate gaat in **begeleidingsmodus**: *"Wat verdrietig, gecondoleerd. Ik help je
stap voor stap, zonder haast: 1) de overlijdensakte, 2) een attest of akte van erfopvolging, 3)
daarna kan een adviseur de rekeningen met je overlopen. Zal ik een gesprek met een adviseur
klaarzetten, zodat je je verhaal niet opnieuw hoeft te doen?"* Daaronder staat het blok
**"Menselijke adviseur"**, met de samenvatting die de adviseur meekrijgt.

**Voice-over:**
> "Er zijn momenten waarop een bank níét moet verkopen. Na een erfenis zou elk systeem
> beleggingen voorstellen. Kate niet. Ze begeleidt Els, en geeft haar door aan een mens die alles
> al weet."

---

### Scène 6 · Zo ziet dit eruit voor 2,3 miljoen klanten (25 s)

**Doel:** antwoorden op de vraag "hoe schaalt dit?".

**Beeld:** `/jury`, het jury-dashboard (PR #30 van Sander).

**Toon:**
1. De KPI **"Kregen bewust niets"**, ± 45 % van de klanten.
2. De verdeling over de kanalen (feed / push / sms / call).
3. De meting **± 0,7 ms per klant**, wat ± 28 CPU-minuten is voor alle 2,3 miljoen klanten.
4. Eén persona-trace: signalen → moment → actie → reden.

**Voice-over:**
> "Dit is dezelfde motor, over tienduizend synthetische klanten. Bijna de helft kreeg bewust
> niets, en dat is precies de bedoeling. Voor alle klanten van KBC is dat minder dan een half uur
> rekenwerk, zonder taalmodel. De AI draait alleen wanneer iemand met Kate praat."

> ⚠️ Controleer de percentages en milliseconden op het dashboard zelf, na de merge van #30.

---

### Scène 7 · Slot: jij beslist (15 s)

**Doel:** eindigen op vertrouwen en controle.

**Persona:** `emma` → Profiel → **"Wat weet en mag Kate?"**

**Klik:**
1. Zet de gegevens over **uitgaven** uit en ga terug naar home. De supermarkt-deal is **weg**; alleen
   "Proficiat met je eerste loon!" blijft staan.
2. Toon kort de ladder per actie: **Uit / Alleen tippen / Klaarzetten / Automatisch**.

**Voice-over:**
> "Elke suggestie zegt waarom. Jij kiest wat Kate mag weten, en wat ze mag doen. Kate 2.0: de
> juiste boodschap, op het juiste moment, via het juiste kanaal. Of bewust helemaal niets."

**Eindbeeld:** de Aikido-screenshot "na", de naam van het project en de URL van de repo.

---

## 5. Voorbereiding van de opname

### Omgeving
1. Start een **verse server**, want alle data zit in het geheugen. Gebruik deze instellingen in
   `.env`:
   - `PASSWORDLESS_LOGIN=true`: inloggen met één klik per persona
   - `ADMIN_USERNAMES=jan`: Jan mag de tijdmachine gebruiken
2. Optioneel, voor de echte stem en Gemini: zet `KATE_LLM_PROVIDER=gemini`, `GEMINI_API_KEY`,
   `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID_FEMALE` en `ELEVENLABS_VOICE_ID_MALE` in `.env`.
   Controleer ze met `cd backend && python -m scripts.check_kate_keys`. Zonder keys werkt alles
   ook, maar met vaste antwoorden en de stem van de browser.
3. Zet de app in de **mobiele weergave** (telefoonkader) en zoom de browser op 125 %, zodat de
   tekst leesbaar is.

### Volgorde van opnemen
Neem **elke scène apart** op en monteer achteraf.
- Neem scène 2 (tijdmachine) **als laatste** op, of herstart daarna de server: de tijdmachine
  verzet de klok voor de hele app.
- Herstart de server ook na scène 3 (Bevestig) en scène 7 (toestemming uit), zodat die
  wijzigingen andere scènes niet beïnvloeden.

### Checklist vlak voor de opname
- [ ] PR #29 en #48 zijn gemerged (Sofie, Lucas, Els bestaan)
- [ ] PR #30 is gemerged (jury-dashboard)
- [ ] Verse server, `PASSWORDLESS_LOGIN=true`, `ADMIN_USERNAMES=jan`
- [ ] Keys gecontroleerd met `check_kate_keys`, of bewust gekozen voor demomodus
- [ ] Microfoon getest voor scène 5 (spraak)
- [ ] Meldingen van de computer uit, geen persoonlijke tabbladen zichtbaar
- [ ] Aikido-screenshot "na" klaar voor het eindbeeld

---

## 6. Wat nog gebouwd moet worden voor de demo

Dit mist nog om zonder plan B op te nemen, in volgorde van belang.

| Wat | Waarom nodig | Eigenaar |
|---|---|---|
| **"Bewust niet gezegd"** zichtbaar in de app (`silenced` uit `GET /kate/feed`) | De kern van scène 1: nu staat de stilte alleen in de API | David (UI) |
| **Kanaal- en urgentie-badge** op de kaart (push / sms / call) | Scène 1 en 2: laat zien dat Kate van kanaal wisselt | David (UI) |
| **Tijdmachine-knop**, alleen voor admin | Scène 2 zonder Swagger | David (UI) |
| **Twee telefoons naast elkaar** | Scène 1 in één beeld | David (UI) |
| Luxepakket in `Holdings` van Sofie, zodat die kaart een *Bevestig*-knop krijgt | Scène 3: nu heeft kaart 2 nog geen knop | David (Skills) |
| `"u_lucas": "male"` in `kate/voices.py` | Lucas krijgt nu nog de vrouwenstem | Sander |
| Jury-dashboard mergen | Scène 6 | Sander (PR #30) |
| PR #29 en #48 mergen | Sofie, Lucas en Els bestaan pas daarna | review |

## 7. Plan B

| Ontbreekt bij de opname | Vervang door |
|---|---|
| Twee telefoons naast elkaar | Na elkaar opnemen, met een harde knip |
| Stilte niet zichtbaar in de app | De persona-trace van Lucas op `/jury`, of een tekst-overlay in de montage met de echte reden |
| Tijdmachine-knop | Swagger (`/api/docs`, alleen in dev), daarna home verversen |
| Jury-dashboard | De benchmarkcijfers als slide |
| Keys werken niet | Demomodus: dezelfde teksten, met de stem van de browser |
| Een persona ontbreekt (PR niet gemerged) | Scène schrappen. Scène 1 kan met Emma alleen; scène 3 en 5 vallen weg |

---

## 8. Voice-over in één stuk

Om voor te lezen of in te spreken (± 2 min 30 s aan spreektekst):

> KBC's Kate herkent vandaag meer dan honderdveertig situaties, allemaal met de hand geschreven.
> Kate 2.0 stelt ze samen uit signalen in je eigen transacties. Emma en Lucas doen allebei hun
> boodschappen in één supermarkt. Emma krijgt de deal. Lucas niet: zijn huur staat op het spel,
> dus Kate waarschuwt hem en houdt de reclame bewust in. Een voorstel dat geld kost, wacht tot je
> buffer in orde is. Een voorstel dat je geld bespaart, wacht nooit.
>
> We spoelen veertig dagen vooruit. Jans loon komt niet. Kate wacht niet tot hij de app opent,
> maar kiest het kanaal dat past bij de ernst: een sms. Hoogstens één onderbreking per week, dus
> Jan wordt niet overspoeld.
>
> Sofie spaart al, maar ze doet het elke maand met de hand. Kate zet dat om in een vaste
> opdracht, met háár bedrag en háár dag. En ja: Kate stelt ook voor om minder te betalen. Een
> bank die zichzelf geld kost, dat is vertrouwen.
>
> Eén zin in plaats van vijf schermen. Kate vult alles in, maar betaalt nooit zelf iemand anders.
> Jij bevestigt, op het gewone, beveiligde scherm.
>
> Er zijn momenten waarop een bank níét moet verkopen. Na een erfenis zou elk systeem beleggingen
> voorstellen. Kate niet. Ze begeleidt Els, en geeft haar door aan een mens die alles al weet.
>
> Dit is dezelfde motor, over tienduizend synthetische klanten. Bijna de helft kreeg bewust
> niets, en dat is precies de bedoeling. Voor alle klanten van KBC is dat minder dan een half uur
> rekenwerk, zonder taalmodel. De AI draait alleen wanneer iemand met Kate praat.
>
> Elke suggestie zegt waarom. Jij kiest wat Kate mag weten, en wat ze mag doen. Kate 2.0: de
> juiste boodschap, op het juiste moment, via het juiste kanaal. Of bewust helemaal niets.
