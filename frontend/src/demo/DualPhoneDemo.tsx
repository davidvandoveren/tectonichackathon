import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { getDemoUsers } from "../api/auth";
import type { DemoUser } from "../api/types";
import type { SessionSlot } from "../lib/sessionSlot";
import styles from "./DualPhoneDemo.module.css";

const DEVICE_HEIGHT = 868;
const DEVICE_WIDTH = 414;
const CHROME_HEIGHT = 120; // title + persona pickers above the phones
const PHONES: { slot: SessionSlot; label: string; fallback: string }[] = [
  { slot: "a", label: "Gsm A", fallback: "emma" },
  { slot: "b", label: "Gsm B", fallback: "marie" },
];

function phoneSrc(slot: SessionSlot, persona: string): string {
  return `/login?slot=${slot}&as=${encodeURIComponent(persona)}`;
}

/**
 * Demo page (/duo): two real-size iPhones side by side, each running the whole app with its own session
 * (`?slot=a|b`), so the jury sees how Kate treats two customers differently at the same time.
 */
export function DualPhoneDemo() {
  const [users, setUsers] = useState<DemoUser[]>([]);
  const [personas, setPersonas] = useState<Record<SessionSlot, string>>({ a: "emma", b: "marie" });
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    getDemoUsers(controller.signal)
      .then(setUsers)
      .catch(() => setUsers([]));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const fit = () => {
      const scale = Math.min(
        0.9,
        (window.innerHeight - CHROME_HEIGHT) / DEVICE_HEIGHT,
        (window.innerWidth - 96) / (2 * DEVICE_WIDTH),
      );
      stageRef.current?.style.setProperty("--phone-scale", String(Math.max(scale, 0.35)));
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>Kate · twee klanten naast elkaar</h1>
        <Link to="/" className={styles.back}>
          Terug naar de app
        </Link>
      </header>

      <div ref={stageRef} className={styles.stage}>
        {PHONES.map(({ slot, label }) => (
          <section key={slot} className={styles.column} aria-label={label}>
            <label className={styles.picker}>
              <span>{label}</span>
              <select
                value={personas[slot]}
                onChange={(event) => setPersonas((current) => ({ ...current, [slot]: event.target.value }))}
              >
                {(users.length ? users : [{ username: personas[slot], display_name: personas[slot], persona: "" }]).map(
                  (user) => (
                    <option key={user.username} value={user.username}>
                      {user.display_name}
                      {user.persona ? ` – ${user.persona}` : ""}
                    </option>
                  ),
                )}
              </select>
            </label>
            <div className={styles.slot}>
              <div className={styles.device}>
                <div className={styles.screen}>
                  <iframe
                    key={personas[slot]}
                    className={styles.frame}
                    src={phoneSrc(slot, personas[slot])}
                    title={`${label}: ${personas[slot]}`}
                    allow="microphone"
                  />
                </div>
              </div>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
