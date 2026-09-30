import { useEffect, useState } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import {
  CHANNEL_LABELS,
  MOMENT_LABELS,
  getDashboard,
  type Dashboard,
  type PersonaTrace,
  type Population,
} from "./dashboardApi";
import styles from "./DashboardPage.module.css";

const SIZES = [1000, 10000] as const;
const nl = new Intl.NumberFormat("nl-BE");
const pctNl = new Intl.NumberFormat("nl-BE", { maximumFractionDigits: 1 });
const pct = (part: number, whole: number) => pctNl.format(whole ? (part / whole) * 100 : 0);

/** Jury dashboard: what Kate does for a whole population, and what she deliberately doesn't. */
export function DashboardPage() {
  const [size, setSize] = useState<number>(10000);
  const [result, setResult] = useState<{ size: number; data?: Dashboard; error?: string } | null>(null);
  const loading = result?.size !== size;
  const data = loading ? null : (result?.data ?? null);
  const error = loading ? null : (result?.error ?? null);

  useEffect(() => {
    const controller = new AbortController();
    getDashboard(size, controller.signal)
      .then((dashboard) => setResult({ size, data: dashboard }))
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setResult({
          size,
          error:
            err instanceof ApiError && err.status === 404
              ? "Dit dashboard is alleen voor de demo-beheerder."
              : err instanceof ApiError
                ? err.detail
                : "Kan het dashboard niet laden.",
        });
      });
    return () => controller.abort();
  }, [size]);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Jury-dashboard · prototype · synthetische data</p>
          <h1 className={styles.title}>Kate voor {nl.format(size)} klanten</h1>
          <p className={styles.subtitle}>
            Elk getal hieronder is geteld uit de echte beslissingen van Kate's brein, per klant uitgevoerd. Niets is
            ingetypt.
          </p>
        </div>
        <div className={styles.controls} role="radiogroup" aria-label="Aantal klanten">
          {SIZES.map((option) => (
            <button
              key={option}
              type="button"
              role="radio"
              aria-checked={size === option}
              className={`${styles.segment} ${size === option ? styles.segmentOn : ""}`}
              onClick={() => setSize(option)}
            >
              {nl.format(option)}
            </button>
          ))}
          <Link to="/" className={styles.back}>
            Terug naar de app
          </Link>
        </div>
      </header>

      {loading && (
        <p className={styles.loading} role="status">
          Kate's brein draait over {nl.format(size)} synthetische klanten…
        </p>
      )}
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      {data && (
        <>
          <Headline population={data.population} />
          <Split population={data.population} />
          <div className={styles.grid}>
            <BarList
              title="Welke momenten Kate herkende"
              caption="Aantal klanten per herkend moment (een klant kan er meerdere hebben)."
              rows={Object.entries(data.population.by_moment).map(([key, value]) => ({
                key,
                label: MOMENT_LABELS[key] ?? key,
                value,
              }))}
            />
            <BarList
              title="Via welk kanaal"
              caption="Hoe dringender, hoe directer. Hoogstens één onderbreking per klant per week."
              rows={Object.entries(data.population.by_channel).map(([key, value]) => ({
                key,
                label: CHANNEL_LABELS[key] ?? key,
                value,
              }))}
            />
            <BarList
              title="Waarom Kate zweeg"
              caption="Momenten die Kate zag maar bewust niet uitsprak."
              rows={Object.entries(data.population.silence_reasons).map(([key, value]) => ({
                key,
                label: data.population.silence_labels[key] ?? key,
                value,
              }))}
            />
            <Scale population={data.population} />
          </div>
          <Archetypes population={data.population} />
          <Personas personas={data.personas} />
        </>
      )}
    </div>
  );
}

function Headline({ population: p }: { population: Population }) {
  const tiles = [
    { label: "Klanten", value: nl.format(p.size), note: "synthetisch, reproduceerbaar" },
    {
      label: "Kregen iets van Kate",
      value: `${pct(p.with_message, p.size)}%`,
      note: `${nl.format(p.with_message)} klanten`,
    },
    {
      label: "Werden onderbroken",
      value: `${pct(p.interrupted, p.size)}%`,
      note: "push, sms of telefoon",
    },
    {
      label: "Kregen bewust niets",
      value: `${pct(p.silent, p.size)}%`,
      note: `${nl.format(p.silent)} klanten: niet spammen is een feature`,
      hero: true,
    },
  ];
  return (
    <section className={styles.tiles} aria-label="Kerncijfers">
      {tiles.map((tile) => (
        <div key={tile.label} className={`${styles.tile} ${tile.hero ? styles.tileHero : ""}`}>
          <p className={styles.tileLabel}>{tile.label}</p>
          <p className={styles.tileValue}>{tile.value}</p>
          <p className={styles.tileNote}>{tile.note}</p>
        </div>
      ))}
    </section>
  );
}

function Split({ population: p }: { population: Population }) {
  const feedOnly = p.with_message - p.interrupted;
  const parts = [
    { key: "feed", label: "Rustig kaartje in de app", value: feedOnly, className: styles.s1 },
    { key: "interrupt", label: "Onderbreking (push, sms, telefoon)", value: p.interrupted, className: styles.s2 },
    { key: "silent", label: "Bewust niets", value: p.silent, className: styles.s3 },
  ];
  return (
    <section className={styles.card} aria-labelledby="split-title">
      <h2 id="split-title" className={styles.cardTitle}>
        Wat elke klant krijgt
      </h2>
      <div className={styles.stack} role="img" aria-label={parts.map((x) => `${x.label}: ${pct(x.value, p.size)}%`).join(", ")}>
        {parts.map((part) =>
          part.value > 0 ? (
            <div
              key={part.key}
              className={`${styles.segmentBar} ${part.className}`}
              style={{ flexGrow: part.value }}
              title={`${part.label}: ${nl.format(part.value)} klanten (${pct(part.value, p.size)}%)`}
            />
          ) : null
        )}
      </div>
      <ul className={styles.legend}>
        {parts.map((part) => (
          <li key={part.key}>
            <span className={`${styles.swatch} ${part.className}`} aria-hidden="true" />
            <span className={styles.legendLabel}>{part.label}</span>
            <strong>{pct(part.value, p.size)}%</strong>
            <span className={styles.muted}>({nl.format(part.value)})</span>
          </li>
        ))}
      </ul>
      <p className={styles.muted}>
        Van wie niets kreeg: {nl.format(p.nothing_at_all)} klanten zonder aanleiding, en bij {nl.format(p.held_back)}{" "}
        zag Kate wel iets maar hield ze zich in (te onzeker, of eerst de geldzorgen).
      </p>
    </section>
  );
}

interface Row {
  key: string;
  label: string;
  value: number;
}

function BarList({ title, caption, rows }: { title: string; caption: string; rows: Row[] }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  const sorted = [...rows].sort((a, b) => b.value - a.value);
  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>{title}</h2>
      <p className={styles.caption}>{caption}</p>
      {sorted.length === 0 ? (
        <p className={styles.muted}>Niets om te tonen.</p>
      ) : (
        <ul className={styles.bars}>
          {sorted.map((row) => (
            <li key={row.key} className={styles.barRow} title={`${row.label}: ${nl.format(row.value)}`}>
              <span className={styles.barLabel}>{row.label}</span>
              <span className={styles.barTrack}>
                <span className={styles.bar} style={{ width: `${(row.value / max) * 100}%` }} />
              </span>
              <span className={styles.barValue}>{nl.format(row.value)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Scale({ population: p }: { population: Population }) {
  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>Zo schaalt het</h2>
      <p className={styles.caption}>Gemeten, niet beweerd: de tijd van Kate's brein per klant, zonder LLM.</p>
      <dl className={styles.scale}>
        <div>
          <dt>Mediaan per klant</dt>
          <dd>{p.p50_ms.toLocaleString("nl-BE")} ms</dd>
        </div>
        <div>
          <dt>95e percentiel</dt>
          <dd>{p.p95_ms.toLocaleString("nl-BE")} ms</dd>
        </div>
        <div>
          <dt>Alle {nl.format(p.kbc_customers)} KBC-klanten</dt>
          <dd>≈ {Math.max(1, Math.round(p.full_bank_cpu_minutes))} CPU-minuten</dd>
        </div>
      </dl>
      <p className={styles.muted}>
        Regels draaien gratis voor iedereen; de LLM (Gemini) wordt alleen aangesproken als een klant zelf met Kate
        praat. Parallel over enkele servers is heel KBC in minuten doorgerekend.
      </p>
    </section>
  );
}

function Archetypes({ population: p }: { population: Population }) {
  return (
    <section className={styles.card} aria-labelledby="arch-title">
      <h2 id="arch-title" className={styles.cardTitle}>
        Per type klant
      </h2>
      <p className={styles.caption}>
        Dezelfde Kate, een totaal andere ervaring. (De mix van types is een aanname voor de demo, geen KBC-data.)
      </p>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Type</th>
              <th scope="col">Klanten</th>
              <th scope="col">Kregen iets</th>
              <th scope="col">Onderbroken</th>
              <th scope="col">Bewust niets</th>
              <th scope="col">Meest herkend</th>
            </tr>
          </thead>
          <tbody>
            {p.archetypes.map((row) => (
              <tr key={row.archetype}>
                <th scope="row">{row.label}</th>
                <td>{nl.format(row.customers)}</td>
                <td>{pct(row.with_message, row.customers)}%</td>
                <td>{pct(row.interrupted, row.customers)}%</td>
                <td>{pct(row.silent, row.customers)}%</td>
                <td>{row.top_moments.map((m) => MOMENT_LABELS[m] ?? m).join(", ") || "–"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Personas({ personas }: { personas: PersonaTrace[] }) {
  return (
    <section aria-labelledby="personas-title">
      <h2 id="personas-title" className={styles.sectionTitle}>
        Onder de motorkap: signaal → situatie → actie → reden
      </h2>
      <div className={styles.personaGrid}>
        {personas.map((persona) => (
          <article key={persona.username} className={styles.card}>
            <h3 className={styles.personaName}>{persona.display_name}</h3>
            <p className={styles.muted}>{persona.persona}</p>
            <ol className={styles.flow}>
              <li>
                <span className={styles.step}>Signalen</span>
                {persona.signals.length ? (
                  <ul>
                    {persona.signals.map((s) => (
                      <li key={s.type}>{s.evidence}</li>
                    ))}
                  </ul>
                ) : (
                  <p className={styles.muted}>Geen opvallende signalen.</p>
                )}
              </li>
              <li>
                <span className={styles.step}>Situatie</span>
                <p>
                  {persona.moments.length
                    ? persona.moments
                        .map((m) => `${MOMENT_LABELS[m.type] ?? m.type} (zekerheid ${m.confidence})`)
                        .join(" · ")
                    : "Niets dat een actie waard is."}
                </p>
              </li>
              <li>
                <span className={styles.step}>Actie</span>
                {persona.actions.length ? (
                  <ul>
                    {persona.actions.map((a) => (
                      <li key={a.title}>
                        <strong>{a.title}</strong> · {CHANNEL_LABELS[a.channel] ?? a.channel} · urgentie {a.urgency}
                        <span className={styles.reason}>Waarom: {a.reason}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Kate stuurt bewust niets.</p>
                )}
              </li>
              {persona.silenced.length > 0 && (
                <li>
                  <span className={styles.step}>Bewust stil</span>
                  <ul>
                    {persona.silenced.map((s) => (
                      <li key={s.moment}>
                        {MOMENT_LABELS[s.moment] ?? s.moment}: {s.reason}
                      </li>
                    ))}
                  </ul>
                </li>
              )}
            </ol>
          </article>
        ))}
      </div>
    </section>
  );
}
