# Demoscript – video < 3 min

Eigenaar: Alexandre (#42). Eén verhaal in acht scènes, samen ongeveer 175 seconden. Per scène staat erbij welke persona, wat je klikt, wat Kate doet en wat de voice-over zegt. De kolom **Status** geeft aan of iets vandaag al werkt op `main`. Houd die kolom bij tot de opname. Wat bij de opname niet werkt, schrap je (zie *Plan B*).

De rode draad voor de jury: **Kate toont niets op basis van wie iemand is, alleen op basis van wat die klant doet.** Elke scène laat dat zien, en de sectie *Bewijzen dat Kate op gedrag reageert* zegt hoe je het expliciet aantoont.

**Voorbereiding**
- Gebruik de Cloud Run-versie, of draai lokaal met `PASSWORDLESS_LOGIN=true` (één klik per persona) en `ADMIN_USERNAMES=jan` (voor de tijdmachine).
- **Admin = een gebruikersnaam in `ADMIN_USERNAMES`.** Een aparte rol bestaat niet. Standaard is die lijst leeg, en dan geven `/regie` (tijdmachine) en `/jury` (dashboard) aan **iedereen** *"Alleen beschikbaar voor de demo-admin"*, ook aan Jan. Zo stel je het in:
  - **Lokaal:** zet `ADMIN_USERNAMES=jan` en `PASSWORDLESS_LOGIN=true` in `.env`, in de hoofdmap of in `backend/` (zie `.env.example`), en **herstart de backend**. Instellingen worden alleen bij het opstarten gelezen.
  - **Cloud Run:** `ADMIN_USERNAMES=jan PASSWORDLESS_LOGIN=true ./deploy/cloudrun.sh`. Het script zet de variabele alleen door als ze in je shell staat.
  - Wees daarna voor `/regie` en `/jury` **ingelogd als `jan`**. Met Emma, Bram, Sofie of Els blijft de melding staan.
- Zet de sleutels voor Gemini en ElevenLabs in `.env` en controleer ze met `cd backend && python -m scripts.check_kate_keys` (#33). Voor Cloud Run is #62 nodig. Zonder sleutels werkt alles in demomodus, maar dan hoor je de stem van de browser.
- Start elke opname met een **verse server**. Alle data zit in het geheugen, en zowel de tijdmachine als de live overschrijving in scène 4b veranderen de toestand.
- Neem de scènes apart op en monteer ze achteraf. Dan verpest één fout niet de hele opname.
- Zet de app in de modus **Mobiel**, via de schakelaar rechtsonder. Dan staat alles in een telefoonkader.

## Overzicht

Nagekeken op `main` met een generale repetitie via de API op 30/09.

| # | Scène | Persona | Duur | Status |
|---|---|---|---|---|
| 1 | Zelfde app, andere Kate | Emma ↔ Bram | 20 s | ✅ twee telefoons op `/demo` (#76) |
| 2 | Kate houdt zich bewust in | Bram | 25 s | ✅ kaart met urgentiemeter en *Pushbericht*, "Bewust niet gezegd" op home (#60) |
| 3 | Tijdmachine: het loon blijft uit | Jan | 25 s | ✅ knoppen op `/regie` (#60, #78), sms-melding en urgentie 98 |
| 4 | Een gewoonte automatiseren | Sofie | 20 s | ✅ drie kaarten met *Bevestig* (#46, #48) |
| 4b | **Bewijs: Sofie verandert haar gedrag, Kate verandert mee** | Sofie | 15 s | ✅ live overschrijving (nagekeken) |
| 5 | Just say it | Emma | 15 s | ✅ |
| 6 | Erfenis: begeleiden in plaats van verkopen | Els | 25 s | ✅ lege feed, begeleidingsmodus, stem |
| 7 | Zo ziet dit eruit voor 2,3 miljoen klanten | – | 20 s | ✅ `/jury` (#30), de cijfers zijn nieuw (zie scène) |
| | Slot: vertrouwen en veiligheid | – | 10 s | ✅ schakelaar op "Wat weet en mag Kate?" · ⏳ Aikido-screenshot "na" (#55) |

---

## Bewijzen dat Kate op gedrag reageert

Een jury zal denken: *"Die personas zijn toch gewoon zo ingesteld?"* Zo toon je aan dat dat niet klopt. Kies er minstens **drie** voor de video. De vetgedrukte zitten al in de scènes hieronder.

| # | Bewijs | Hoe tonen | Wat de kijker ziet | Waar |
|---|---|---|---|---|
| A | **Gedrag live veranderen** | Sofie zet in de app gewoon € 400 van haar spaarrekening naar haar zichtrekening. Daarna ververs je home. | De kaart "Wil je dit automatisch laten doen?" verdwijnt. Wie geld uit zijn spaarpot haalt, wil op dat moment geen vaste spaaropdracht. | **Scène 4b** |
| B | **Zelfde klant, ander verloop** | Jan krijgt de tijdmachine twee keer, op een verse server: eerst *loon komt binnen*, daarna *loon blijft uit*. | Komt het loon binnen, dan blijft Kate rustig: alleen een deal in de feed. Blijft het uit, dan komt er een sms met urgentie 98 en houdt Kate de deal bewust achter. | **Scène 3** |
| C | **"Waarom zie ik dit?" gebruikt de eigen cijfers** | Klik de reden open en toon meteen daarna de rekeninghistoriek. | Bram: *"Je zichtrekening staat op € 212,40, minder dan je grootste woonkost van de afgelopen twee maanden (€ 720,00)."* Sofie: *"Je betaalde 13 keer bij TotalEnergies Berchem…"* Dezelfde bedragen en winkels staan in de historiek. | **Scène 2**, 4 |
| D | **Gedrag afschermen, de kaart verdwijnt** | Zet bij Sofie op *"Wat weet en mag Kate?"* de schakelaar voor uitgaven uit. | Het spaarvoorstel en de tankdeal verdwijnen, want die steunen op haar uitgaven. Het Luxepakket blijft staan, want dat steunt op haar producten. | **Slot** |
| E | **Dezelfde code, 10 000 onbekenden** | Toon het dashboard `/jury`. | Een verdeling over 10 000 synthetische klanten die niemand met de hand heeft gemaakt. 45,3 % kreeg bewust niets. Met regels per persona kan dat niet. | **Scène 7** |
| F | **De code zelf** (optioneel, 3 s) | Toon `backend/app/moments/signals.py` in de editor. | Elk signaal is een functie die alleen transacties leest. Er staat nergens een naam van een persona in de engine. | Knipper tussen scène 1 en 2, of als slide |

**Zin voor de voice-over, bruikbaar overal:**
> "Niemand heeft deze kaart voor deze klant geschreven. Kate leidt ze af uit wat de klant zelf doet. Verandert dat gedrag, dan verandert Kate mee."

**Wat je daarbij níét zegt:** dat Kate iemands leeftijd, beroep of gezinssituatie kent. De engine leest alleen rekeningen en transacties. Gevoelige uitgaven worden eruit gefilterd voordat er iets berekend wordt: gezondheid, religie, politiek, vakbond en dating (#35).

---

## 1 · Zelfde app, andere Kate (20 s)

**Beeld:** open **`/demo`**: twee iPhones naast elkaar, elk met een eigen sessie (#76). Log links in als **Emma** en rechts als **Bram**. *Plan B:* een gewoon venster (Emma) en een incognitovenster (Bram) naast elkaar, allebei in de modus *Mobiel*.
**Kate:** Emma krijgt "Proficiat met je eerste loon!". Bram krijgt geen reclame, maar een waarschuwing over zijn huur, met een rode urgentiemeter en het label *Pushbericht*.
**Voice-over:**
> "KBC's Kate herkent vandaag meer dan 140 situaties, en die zijn allemaal met de hand geschreven. Hier zie je twee klanten in dezelfde app, met een totaal andere Kate. Niemand heeft dit voor hen geschreven. Kate leidt het af uit wat ze zelf met hun geld doen."

## 2 · Kate houdt zich bewust in (25 s)

**Persona:** `bram`, met € 212,40 op zijn zichtrekening en € 720 huur.
**Klik:** open *Waarom zie ik dit?* op de huurkaart (bewijs C). Klap daarna **"Bewust niet gezegd"** open, onder de carrousel.
**Kate:** `cashflow_risk` met urgentie 91 via **push**. Onder "Bewust niet gezegd": *"Je saldo staat krap. Voorstellen die je geld kosten houden we daarom even voor ons; eerst je rekening."* Dat is zijn supermarkt-deal, die Kate achterhoudt.
**Voice-over:**
> "Wie veel herkent, kan ook veel spammen. Daarom beslist Kate niet alleen wát ze zegt, maar ook wanneer ze moet zwijgen. Zolang je buffer krap is, houdt ze een aanbod dat geld kost achter. Een voorstel dat je geld bespaart, houdt ze nooit achter."

## 3 · Tijdmachine: het loon blijft uit (25 s)

**Persona:** `jan`, de admin.
**Klik:** ga naar **`/regie`** (niet in het menu; `/demo` is de twee-telefoons-weergave van #76) en klik **"+40 dagen · loon blijft uit"**. De app springt terug naar home.
**Kate:** bovenaan verschijnt een **sms-melding**: *"Je loon is nog niet gestort"*. De kaart heeft urgentie **98**, is rood en draagt het label *Sms*. Onder "Bewust niet gezegd" staat de deal.
**Sterker (bewijs B):** neem eerst op een verse server **"+40 dagen · loon komt binnen"** op. Dan blijft Kate rustig. Knip daarna naar "loon blijft uit". De klant en de datum zijn dezelfde, alleen het gedrag verschilt.
**Voice-over:**
> "We spoelen veertig dagen vooruit. Komt Jans loon binnen, dan zwijgt Kate. Blijft het uit, dan stuurt ze geen kaartje in de app, maar een sms: het kanaal dat past bij de ernst. Dat gebeurt hoogstens één keer per week."

## 4 · Een gewoonte automatiseren (20 s)

**Persona:** `sofie`.
**Kate:** drie kaarten, elk met een eigen *Waarom zie ik dit?*:
1. *"Je zet al 4 maanden zelf geld opzij, meestal € 250."* Kate stelt een vaste opdracht voor met **Sofies eigen bedrag en dag**, niet met een bedrag dat de bank kiest.
2. *"Het Luxepakket kost je € 300,00 per jaar, maar we zien geen reizen."* De bank raadt aan om minder te betalen.
3. De deal bij het tankstation waar ze elke week komt.

**Klik:** **Bevestig** op de spaaropdracht. Toon daarna *Wat heeft Kate voor mij gedaan?*
**Voice-over:**
> "Sofie spaart al, maar ze doet het elke maand met de hand. Kate zet dat om in een vaste opdracht, met haar eigen cijfers. Ze ziet ook dat Sofie betaalt voor een reispakket zonder te reizen, en zegt het haar. Eén tik, en de klant beslist zelf."

## 4b · Bewijs: Sofie verandert haar gedrag, Kate verandert mee (15 s)

Neem dit op in een **aparte opname op een verse server**, zonder op *Bevestig* te hebben geklikt.

**Klik:** ga bij Sofie naar *Overschrijving* en zet **€ 400 van haar spaarrekening naar haar zichtrekening**. Ga terug naar home.
**Kate:** de kaart "Wil je dit automatisch laten doen?" is **weg**. Het Luxepakket en de deal blijven staan. Nagekeken: de overschrijving geeft `201`, en de feed gaat van drie naar twee kaarten.
**Voice-over:**
> "We raken niets aan in de code. Sofie haalt geld van haar spaarrekening. Kate ziet dat ze dat geld nu nodig heeft, en stelt niet langer voor om het vast te zetten."

## 5 · Just say it (15 s)

**Persona:** `emma`.
**Klik:** open Kate en typ of zeg *"Stuur Lucas 25 euro voor de pizza"*.
**Kate:** *"Ik heb een overschrijving van € 25,00 naar Lucas klaargezet. Controleer ze en bevestig zelf."* Het gewone overschrijvingsscherm opent, al ingevuld, en Emma bevestigt zelf.
**Voice-over:**
> "Eén zin in plaats van vijf schermen. Kate vult alles in, maar betaalt zelf nooit aan iemand anders. De klant bevestigt op het gewone, gevalideerde scherm."

## 6 · Erfenis: begeleiden in plaats van verkopen (25 s)

**Persona:** `els`. Haar mama overleed onlangs. De historiek toont de uitvaart, de notaris en de uitkering van de nalatenschap.
**Klik:** toon eerst dat de feed van Els **leeg** is. Zeg dan tegen Kate *"Mijn mama is overleden, wat moet ik met de erfenis doen?"* (gesproken, met de stem).
**Kate:** schakelt naar de **begeleidingsmodus**. Ze begint met *"Wat verschrikkelijk, gecondoleerd. Neem gerust je tijd."* en geeft dan een stappenplan zonder marketing. Ze biedt aan een adviseur in te schakelen, met een samenvatting, zodat Els haar verhaal niet opnieuw moet vertellen.
**Voice-over:**
> "Er is een moment waarop een bank níét moet verkopen. De uitkering van een erfenis lijkt op geld dat klaarstaat om belegd te worden. Kate herkent wat het echt is, begeleidt Els en geeft haar door aan een mens, met de volledige context."

## 7 · Zo ziet dit eruit voor 2,3 miljoen klanten (20 s)

**Beeld:** `/jury`, het jury-dashboard over 10 000 synthetische klanten. Alleen voor de admin, dus log in als `jan`.
**Toon:** de KPI **"Kregen bewust niets": 45,3 %**, de verdeling over de kanalen (feed, push, sms, bellen) en de meting per klant. Gemeten op 30/09: **p50 1,3 ms per klant**, ongeveer **56 CPU-minuten** voor alle 2,3 miljoen klanten, zonder AI-model. Die tijd hangt af van de machine. **Lees ze af van het scherm op de dag van de opname** en pas de voice-over aan.
**Voice-over:**
> "Dit is dezelfde motor, gedraaid over tienduizend klanten die niemand met de hand heeft gemaakt. Bijna de helft kreeg bewust niets, en dat is precies de bedoeling. Voor alle klanten van KBC is het ongeveer een uur rekenwerk op één processor, zonder taalmodel. Het dure AI-deel draait alleen als iemand met Kate praat."

## Slot · Vertrouwen en veiligheid (10 s)

**Beeld:** bij Sofie het scherm *"Wat weet en mag Kate?"*. Zet de schakelaar voor **uitgaven** uit en ga terug naar home (bewijs D). Alleen de kaart over het Luxepakket blijft staan. Toon daarna de Aikido-screenshot "na".
**Voice-over:**
> "Elke suggestie zegt waarom. Jij kiest wat Kate mag weten en wat ze mag doen. Kate 2.0: de juiste boodschap, op het juiste moment, via het juiste kanaal, of bewust helemaal niets."

---

## Plan B (als iets niet af is bij de opname)

| Ontbreekt | Vervang door |
|---|---|
| Twee vensters naast elkaar | Na elkaar inloggen, met een harde knip |
| Stiltes niet zichtbaar in de UI | Persona-trace van Bram op `/jury` |
| `/regie` werkt niet (niet ingelogd als admin) | Controleer `ADMIN_USERNAMES=jan`, of gebruik een `curl` naar `POST /api/v1/admin/time-machine` en ververs home |
| *Bevestig*-knop op kaart | Scène 4 inkorten, of vervangen door `python scripts/skills_tour.py --persona sofie` (#38) in een terminal |
| Live overschrijving (4b) lukt niet | Bewijs D (schakelaar) of B (tijdmachine twee keer) is ook voldoende |
| Jury-dashboard | De benchmarkcijfers als slide |
| API-sleutels werken niet | Demomodus: browserstem en vaste antwoorden. Scène 6 werkt dan nog, maar klinkt minder goed |
