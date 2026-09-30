import { useContext, useEffect, useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import { AuthContext } from "../auth/AuthContext";
import {
  fetchSpeech,
  getKateStatus,
  getKateVoice,
  setKateVoice,
  sendKateMessage,
  transcribe,
  transferLink,
  type ChatTurn,
  type KateAction,
  type KateStatus,
  type VoiceKind,
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
import {
  CloseIcon,
  LeafIcon,
  MicIcon,
  SendIcon,
  ShieldIcon,
  SparkleIcon,
  SpeakerIcon,
  SpeakerOffIcon,
  StopIcon,
} from "./icons";
import styles from "./KateChat.module.css";
import { OPEN_KATE_EVENT } from "./openKate";

interface Message extends ChatTurn {
  id: number;
  action?: KateAction;
  guidance?: boolean;
}

/** Shown on screen and sent as Kate's first turn: she has already said she is an AI. */
const GREETING =
  "Hallo, ik ben Kate, je digitale assistent. Ik ben een AI. Vraag me iets over je geld, of zeg bv. “Stuur Lucas 25 euro voor de pizza”.";

const SUGGESTIONS = [
  "Hoeveel gaf ik deze maand uit?",
  "Wat is mijn saldo?",
  "Stuur Lucas 25 euro voor de pizza",
  "Mijn moeder is overleden, wat moet ik doen?",
];

type MicState = "idle" | "listening" | "transcribing";
type StopHandle = Recording | { stop: () => void };

interface KateChatProps {
  /** Hide the floating launcher when the layout has its own entry point (desktop header). */
  hideLauncher?: boolean;
}

/** Kate: chat + voice. Icon top right (or `openKate()`), opens a full-screen conversation. */
export function KateChat({ hideLauncher = false }: KateChatProps) {
  const auth = useContext(AuthContext);
  const firstName = auth?.user?.first_name;
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<KateStatus | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speakReplies, setSpeakReplies] = useState(false);

  useEffect(() => {
    const handleOpen = () => setOpen(true);
    window.addEventListener(OPEN_KATE_EVENT, handleOpen);
    return () => window.removeEventListener(OPEN_KATE_EVENT, handleOpen);
  }, []);
  const [voice, setVoice] = useState<VoiceKind>("female");
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const [mic, setMic] = useState<MicState>("idle");
  const recording = useRef<StopHandle | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const nextId = useRef(1);
  const listEnd = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open || status) return;
    const controller = new AbortController();
    getKateVoice(controller.signal)
      .then((settings) => setVoice(settings.voice))
      .catch(() => undefined);
    getKateStatus(controller.signal)
      .then(setStatus)
      .catch(() => setStatus({ llm: "mock", voice: false, speech_recognition: false }));
    return () => controller.abort();
  }, [open, status]);

  useEffect(() => {
    listEnd.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  useEffect(() => () => stopAudio(), []);

  function stopAudio() {
    audio.current?.pause();
    stopBrowserSpeech();
    setSpeakingId(null);
  }

  async function chooseVoice(kind: VoiceKind) {
    stopAudio();
    setVoice(kind);
    try {
      setVoice((await setKateVoice(kind)).voice);
    } catch {
      // keep the local choice; the next load resyncs
    }
  }

  function close() {
    stopAudio();
    setOpen(false);
  }

  async function speak(id: number, text: string) {
    stopAudio();
    setSpeakingId(id);
    if (status?.voice) {
      try {
        const url = URL.createObjectURL(await fetchSpeech(text));
        audio.current = new Audio(url);
        audio.current.onended = () => {
          URL.revokeObjectURL(url);
          setSpeakingId(null);
        };
        await audio.current.play();
        return;
      } catch {
        // fall through to the browser voice
      }
    }
    speakWithBrowser(text, () => setSpeakingId(null), voice);
  }

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
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
      const id = nextId.current++;
      setMessages((current) => [
        ...current,
        { id, role: "kate", text: response.reply, action: response.action, guidance: response.mode === "guidance" },
      ]);
      if (speakReplies) void speak(id, response.reply);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Kate is even niet bereikbaar.");
    } finally {
      setBusy(false);
    }
  }

  async function stopListening() {
    const current = recording.current;
    recording.current = null;
    const result = current?.stop();
    if (!(result instanceof Promise)) return; // browser recognition resolves in startListening
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

  async function startListening() {
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
        setError("Spraak wordt niet ondersteund in deze browser. Typ gerust je vraag.");
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
    if (hideLauncher) return null;
    return (
      <button type="button" className={styles.launcher} onClick={() => setOpen(true)} aria-label="Open Kate">
        <SparkleIcon width={20} height={20} />
        <span>Kate</span>
      </button>
    );
  }

  const guidance = messages.some((m) => m.guidance);
  const empty = messages.length === 0;

  return (
    <section className={styles.panel} role="dialog" aria-modal="true" aria-label="Kate, je digitale assistent">
      <header className={styles.header}>
        <div className={styles.identity}>
          <span className={styles.avatar} aria-hidden="true">
            K<span className={styles.onlineDot} />
          </span>
          <div>
            <h2 className={styles.title}>Kate</h2>
            <p className={styles.subtitle}>
              <span className={styles.aiBadge}>AI</span> Digitale assistent
              {status?.llm === "mock" ? " · demo-modus" : ""}
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.iconButton}
            aria-pressed={speakReplies}
            aria-label={speakReplies ? "Kate spreekt antwoorden uit (aan)" : "Kate spreekt antwoorden uit (uit)"}
            onClick={() => {
              if (speakReplies) stopAudio();
              setSpeakReplies((value) => !value);
            }}
          >
            {speakReplies ? <SpeakerIcon /> : <SpeakerOffIcon />}
          </button>
          <button type="button" className={styles.iconButton} onClick={close} aria-label="Sluit Kate">
            <CloseIcon />
          </button>
        </div>
      </header>

      {speakReplies && (
        <div className={styles.voiceBar} role="radiogroup" aria-label="Stem van Kate">
          <span>Stem van Kate</span>
          {(["female", "male"] as const).map((kind) => (
            <button
              key={kind}
              type="button"
              role="radio"
              aria-checked={voice === kind}
              className={`${styles.voiceOption} ${voice === kind ? styles.voiceSelected : ""}`}
              onClick={() => void chooseVoice(kind)}
            >
              {kind === "female" ? "Vrouw" : "Man"}
            </button>
          ))}
        </div>
      )}

      {guidance && (
        <p className={styles.guidanceBanner}>
          <LeafIcon width={18} height={18} /> Begeleidingsmodus: stap voor stap, zonder reclame.
        </p>
      )}

      <div className={styles.messages} aria-live="polite">
        {empty && (
          <div className={styles.welcome}>
            <span className={styles.welcomeAvatar} aria-hidden="true">
              <SparkleIcon width={32} height={32} />
            </span>
            <h3 className={styles.welcomeTitle}>Hoi{firstName ? ` ${firstName}` : ""}, waarmee kan ik helpen?</h3>
            <p className={styles.welcomeText}>{GREETING}</p>
            <div className={styles.suggestions}>
              {SUGGESTIONS.map((suggestion) => (
                <button key={suggestion} type="button" className={styles.chip} onClick={() => void send(suggestion)}>
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message) =>
          message.role === "user" ? (
            <div key={message.id} className={styles.userRow}>
              <p className={`${styles.bubble} ${styles.user}`}>{message.text}</p>
            </div>
          ) : (
            <div key={message.id} className={styles.kateRow}>
              <span className={styles.miniAvatar} aria-hidden="true">
                K
              </span>
              <div className={styles.kateContent}>
                <p className={`${styles.bubble} ${styles.kate}`}>{message.text}</p>
                <button
                  type="button"
                  className={styles.readAloud}
                  onClick={() => (speakingId === message.id ? stopAudio() : void speak(message.id, message.text))}
                >
                  {speakingId === message.id ? <StopIcon width={14} height={14} /> : <SpeakerIcon width={14} height={14} />}
                  {speakingId === message.id ? "Stop" : "Voorlezen"}
                </button>
                {message.action && <ActionCard action={message.action} onNavigate={close} />}
              </div>
            </div>
          )
        )}

        {busy && (
          <div className={styles.kateRow}>
            <span className={styles.miniAvatar} aria-hidden="true">
              K
            </span>
            <p className={`${styles.bubble} ${styles.kate} ${styles.typing}`} aria-label="Kate denkt na">
              <span />
              <span />
              <span />
            </p>
          </div>
        )}
        <div ref={listEnd} />
      </div>

      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}

      {mic === "listening" ? (
        <div className={styles.listening}>
          <span className={styles.wave} aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </span>
          <p className={styles.listeningText}>Ik luister… tik om te stoppen</p>
          <button type="button" className={styles.stopButton} onClick={() => void stopListening()} aria-label="Stop met opnemen">
            <StopIcon />
          </button>
        </div>
      ) : (
        <form className={styles.composer} onSubmit={onSubmit}>
          <div className={styles.inputWrap}>
            <input
              ref={inputRef}
              className={styles.input}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder={mic === "transcribing" ? "Even omzetten naar tekst…" : "Vraag het aan Kate"}
              maxLength={1000}
              aria-label="Bericht aan Kate"
              disabled={mic === "transcribing"}
            />
            {input.trim() ? (
              <button type="submit" className={styles.send} disabled={busy} aria-label="Stuur">
                <SendIcon width={20} height={20} />
              </button>
            ) : (
              <button
                type="button"
                className={styles.mic}
                onClick={() => void startListening()}
                disabled={mic === "transcribing" || busy}
                aria-label="Spreek tegen Kate"
              >
                <MicIcon width={20} height={20} />
              </button>
            )}
          </div>
          <p className={styles.footnote}>
            <ShieldIcon width={14} height={14} /> Kate is een AI en kan zich vergissen. Ze ziet alleen jouw eigen gegevens.
          </p>
        </form>
      )}
    </section>
  );
}

function ActionCard({ action, onNavigate }: { action: KateAction; onNavigate: () => void }) {
  const [requested, setRequested] = useState(false);

  if (action.type === "transfer") {
    return (
      <div className={styles.actionCard}>
        <p className={styles.actionEyebrow}>Voorstel · jij beslist</p>
        <p className={styles.actionTitle}>Overschrijving klaargezet</p>
        <dl className={styles.actionDetails}>
          <dt>Aan</dt>
          <dd>{action.to_name}</dd>
          <dt>Bedrag</dt>
          <dd>€ {action.amount?.replace(".", ",")}</dd>
          {action.description && (
            <>
              <dt>Mededeling</dt>
              <dd>{action.description}</dd>
            </>
          )}
        </dl>
        <Link to={transferLink(action)} className={styles.actionButton} onClick={onNavigate}>
          Controleer en bevestig
        </Link>
        <p className={styles.actionNote}>Kate voert niets zelf uit. Jij bevestigt.</p>
      </div>
    );
  }

  if (action.type === "advisor_handoff") {
    return (
      <div className={`${styles.actionCard} ${styles.advisorCard}`}>
        <p className={styles.actionEyebrow}>Menselijke adviseur</p>
        <p className={styles.actionTitle}>Gesprek voorbereid</p>
        <p className={styles.actionNote}>Dit krijgt je adviseur mee, zodat je je verhaal niet opnieuw hoeft te doen:</p>
        <blockquote className={styles.summary}>{action.summary}</blockquote>
        <button type="button" className={styles.actionButton} onClick={() => setRequested(true)} disabled={requested}>
          {requested ? "Aangevraagd ✓ (demo)" : "Plan een gesprek"}
        </button>
      </div>
    );
  }

  return null;
}
