import { Link } from "react-router";
import styles from "./PrivacyPage.module.css";

const REPO_URL = "https://github.com/davidvandoveren/tectonichackathon";

/**
 * Privacy, AI transparency and disclaimer. Public (reachable before login) so anyone can read
 * what the prototype does with data before trying it. Keep it in sync with the backend: every
 * claim here must stay true (see docs/security-and-compliance.md).
 */
export function PrivacyPage() {
  return (
    <div className={styles.page}>
      <article className={styles.article}>
        <h1 className={styles.title}>Privacy &amp; AI</h1>

        <section className={styles.notice} aria-label="Disclaimer">
          <p>
            <strong>Dit is een prototype</strong>, gebouwd voor de Tectonic Hackathon (KBC-case). Het is
            geen echte bankapp en geen officieel product of dienst van KBC. Alle klanten, rekeningen en
            transacties zijn verzonnen. Vul nooit echte persoonsgegevens, rekeningnummers of
            wachtwoorden in.
          </p>
        </section>

        <section>
          <h2>Welke gegevens?</h2>
          <p>
            Alleen synthetische demodata. Wat je zelf doet (overschrijvingen, chatberichten, keuzes)
            staat enkel in het geheugen van de server en verdwijnt bij elke herstart. Geen database,
            geen tracking, geen analytics, geen advertenties.
          </p>
        </section>

        <section>
          <h2>Cookies en opslag</h2>
          <p>
            Eén strikt noodzakelijke sessiecookie (HttpOnly, Secure, SameSite=Strict) houdt je
            aangemeld; ze vervalt na maximaal een uur of zodra je afmeldt. In je browser bewaren we
            alleen je weergavekeuze (mobiel of desktop). Er zijn geen tracking- of marketingcookies,
            daarom is er geen cookiebanner.
          </p>
        </section>

        <section>
          <h2>Kate is een AI</h2>
          <ul>
            <li>Je weet altijd dat je met een AI praat (EU AI Act, art. 50).</li>
            <li>
              Kate stelt voor, jij beslist. Een betaling naar iemand anders voert ze nooit zelf uit: jij
              controleert en bevestigt. Wat ze automatisch mag doen, kies jij per actie, binnen een
              limiet die je zelf instelt.
            </li>
            <li>
              Geen geautomatiseerde beslissingen over krediet, beleggen of verzekeren (AVG art. 22):
              daarvoor krijg je altijd een menselijke adviseur.
            </li>
            <li>Kate kan zich vergissen. Controleer haar voorstellen.</li>
          </ul>
        </section>

        <section>
          <h2>Gevoelige uitgaven</h2>
          <p>
            Uitgaven die iets zeggen over gezondheid, geloof, politieke voorkeur, vakbond of relaties
            (AVG art. 9) worden geneutraliseerd voor ze naar Kate&apos;s AI-model gaan, en de
            abonnementenbeheerder toont ze niet.
          </p>
        </section>

        <section>
          <h2>Externe diensten</h2>
          <p>Alleen als het team ze heeft aangezet:</p>
          <ul>
            <li>
              <strong>Google Gemini</strong> krijgt je chatvraag en een beperkte samenvatting van je
              (synthetische) rekeningen: saldi, uitgaven per categorie en recente transacties, zonder
              rekeningnummers.
            </li>
            <li>
              <strong>ElevenLabs</strong> krijgt de tekst die Kate voorleest, en je spraakopname als je
              de microfoon gebruikt. De microfoon werkt pas na jouw toestemming in de browser, en alleen
              tijdens het opnemen.
            </li>
          </ul>
          <p>
            Zonder die diensten werkt Kate met vaste demo-antwoorden en met de spraakfuncties van je
            browser. Afhankelijk van je browser verwerkt de browsermaker dan je spraak.
          </p>
        </section>

        <section>
          <h2>Beveiliging</h2>
          <p>
            Sessies staan op de server, wachtwoorden zijn gehasht (scrypt), elke vraag wordt gecontroleerd
            op eigenaarschap en elke overschrijving op de bankregels. Een kwetsbaarheid gevonden? Meld ze
            vertrouwelijk via{" "}
            <a href={`${REPO_URL}/security/advisories/new`} target="_blank" rel="noopener noreferrer">
              GitHub Security Advisories
            </a>
            , zie ook{" "}
            <a href={`${REPO_URL}/blob/main/SECURITY.md`} target="_blank" rel="noopener noreferrer">
              SECURITY.md
            </a>
            .
          </p>
        </section>

        <Link to="/" className={styles.back}>
          Terug naar de app
        </Link>
      </article>
    </div>
  );
}
