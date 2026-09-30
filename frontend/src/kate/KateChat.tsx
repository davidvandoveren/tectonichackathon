import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import {
  fetchSpeech,
  getKateStatus,
  sendKateMessage,
  transcribe,
  transferLink,
  type ChatTurn,
  type KateAction,
  type KateStatus,
} from "./kateApi";
import {
  canRecord,
  canUseBrowserRecognition,
  listenWithBrowser,
  speakWithBrowser,
  startRecording,
  stopBrowserSpeech,
  type Recording,
} from "./speech";
import styles from "./KateChat.module.css";

interface Message extends ChatTurn {
  id: number;
  action?: KateAction;
  guidance?: boolean;
}

const GREETING =
  "Hallo, ik ben Kate, je digitale assistent. Ik ben een AI. Vraag me iets over je geld, of zeg bv. “Stuur Lucas 25 euro voor de pizza”.";

type MicState = "idle" | "listening" | "transcribing";

/** Kate: chat + voice. Icon top right, opens a full-screen panel. */
export function KateChat() {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<KateStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speakReplies, setSpeakReplies] = useState(false);
  const [mic, setMic] = useState<MicState>("idle");
  const recording = useRef<Recording | { stop: () => void } | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const nextId = useRef(1);
  const listEnd = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open || status) return;
    const controller = new AbortController();
    getKateStatus(controller.signal)
      .then(setStatus)
      .catch(() => setStatus({ llm: "mock", voice: false, speech_recognition: false }));
    return () => controller.abort();
  }, [open, status]);

  useEffect(() => {
    listEnd.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, busy]);

  useEffect(() => () => stopAudio(), []);

  function stopAudio() {
    audio.current?.pause();
    stopBrowserSpeech();
  }

  async function speak(text: string) {
    stopAudio();
    if (status?.voice) {
      try {
        const url = URL.createObjectURL(await fetchSpeech(text));
        audio.current = new Audio(url);
        audio.current.onended = () => URL.revokeObjectURL(url);
        await audio.current.play();
        return;
      } catch {
        // fall through to the browser voice
      }
    }
    speakWithBrowser(text);
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    // The on-screen greeting counts as Kate's first turn: she already said she is an AI.
    const history: ChatTurn[] = [
      { role: "kate", text: GREETING },
      ...messages.map(({ role, text: t }) => ({ role, text: t })),
    ];
    setMessages((current) => [...current, { id: nextId.current++, role: "user", text: message }]);
    setInput("");
    setError(null);
    setBusy(true);
    try {
      const response = await sendKateMessage(message, history);
      setMessages((current) => [
        ...current,
        {
          id: nextId.current++,
          role: "kate",
          text: response.reply,
          action: response.action,
          guidance: response.mode === "guidance",
        },
      ]);
      if (speakReplies) void speak(response.reply);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Kate is even niet bereikbaar.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleMic() {
    if (mic === "listening") {
      const current = recording.current;
      recording.current = null;
      if (current && "stop" in current) {
        const result = current.stop();
        if (result instanceof Promise) {
          setMic("transcribing");
          try {
            const text = await transcribe(await result);
            if (text) await send(text);
            else setError("Ik heb niets verstaan. Probeer opnieuw.");
          } catch (err) {
            setError(err instanceof ApiError ? err.detail : "Spraakherkenning mislukt.");
          } finally {
            setMic("idle");
          }
        }
      }
      return;
    }

    setError(null);
    stopAudio();
    try {
      if (status?.speech_recognition && canRecord()) {
        recording.current = await startRecording();
        setMic("listening");
      } else if (canUseBrowserRecognition()) {
        const listening = listenWithBrowser();
        recording.current = { stop: () => listening.stop() };
        setMic("listening");
        const text = await listening.result;
        recording.current = null;
        setMic("idle");
        if (text) await send(text);
      } else {
        setError("Spraak wordt niet ondersteund in deze browser.");
      }
    } catch {
      recording.current = null;
      setMic("idle");
      setError("Geen toegang tot je microfoon.");
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void send(input);
  }

  if (!open) {
    return (
      <button type="button" className={styles.launcher} onClick={() => setOpen(true)} aria-label="Open Kate">
        <span aria-hidden="true">K</span>
      </button>
    );
  }

  const guidance = messages.some((m) => m.guidance);

  return (
    <section className={styles.panel} role="dialog" aria-modal="true" aria-label="Kate, je digitale assistent">
      <header className={styles.header}>
        <div>
          <h2 className={styles.title}>Kate</h2>
          <p className={styles.subtitle}>
            AI-assistent · prototype{status?.llm === "mock" ? " · demo-modus" : ""}
          </p>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.iconButton}
            aria-pressed={speakReplies}
            onClick={() => {
              if (speakReplies) stopAudio();
              setSpeakReplies((value) => !value);
            }}
            title={speakReplies ? "Kate spreekt antwoorden uit" : "Kate spreekt niet"}
          >
            {speakReplies ? "🔊" : "🔈"}
          </button>
          <button
            type="button"
            className={styles.iconButton}
            onClick={() => {
              stopAudio();
              setOpen(false);
            }}
            aria-label="Sluit Kate"
          >
            ✕
          </button>
        </div>
      </header>

      {guidance && <p className={styles.guidanceBanner}>Begeleidingsmodus: stap voor stap, zonder reclame.</p>}

      <div className={styles.messages} aria-live="polite">
        <p className={`${styles.bubble} ${styles.kate}`}>{GREETING}</p>
        {messages.map((message) => (
          <div key={message.id} className={message.role === "user" ? styles.userRow : styles.kateRow}>
            <p className={`${styles.bubble} ${message.role === "user" ? styles.user : styles.kate}`}>{message.text}</p>
            {message.action && <ActionCard action={message.action} onClose={() => setOpen(false)} />}
          </div>
        ))}
        {busy && <p className={`${styles.bubble} ${styles.kate} ${styles.typing}`}>Kate denkt na…</p>}
        <div ref={listEnd} />
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      <form className={styles.inputRow} onSubmit={onSubmit}>
        <button
          type="button"
          className={`${styles.mic} ${mic === "listening" ? styles.micActive : ""}`}
          onClick={() => void toggleMic()}
          disabled={mic === "transcribing" || busy}
          aria-label={mic === "listening" ? "Stop met opnemen" : "Spreek tegen Kate"}
        >
          {mic === "transcribing" ? "…" : "🎤"}
        </button>
        <input
          className={styles.input}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={mic === "listening" ? "Ik luister…" : "Vraag het aan Kate"}
          maxLength={1000}
          aria-label="Bericht aan Kate"
        />
        <button type="submit" className={styles.send} disabled={busy || !input.trim()}>
          Stuur
        </button>
      </form>
    </section>
  );
}

function ActionCard({ action, onClose }: { action: KateAction; onClose: () => void }) {
  const [requested, setRequested] = useState(false);

  if (action.type === "transfer") {
    return (
      <div className={styles.actionCard}>
        <p className={styles.actionTitle}>Overschrijving klaargezet</p>
        <p>
          € {action.amount?.replace(".", ",")} naar {action.to_name}
          {action.description ? ` · ${action.description}` : ""}
        </p>
        <Link to={transferLink(action)} className={styles.actionButton} onClick={onClose}>
          Controleer en bevestig
        </Link>
        <p className={styles.actionNote}>Kate voert niets zelf uit. Jij bevestigt.</p>
      </div>
    );
  }

  if (action.type === "advisor_handoff") {
    return (
      <div className={styles.actionCard}>
        <p className={styles.actionTitle}>Gesprek met een adviseur</p>
        <p className={styles.actionNote}>Dit krijgt je adviseur mee, zodat je je verhaal niet opnieuw moet doen:</p>
        <p className={styles.summary}>{action.summary}</p>
        <button
          type="button"
          className={styles.actionButton}
          onClick={() => setRequested(true)}
          disabled={requested}
        >
          {requested ? "Aangevraagd ✓ (demo)" : "Plan een gesprek"}
        </button>
      </div>
    );
  }

  return null;
}
