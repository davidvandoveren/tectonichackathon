/**
 * Microphone recording (for server-side speech recognition) and browser fallbacks
 * (Web Speech API) used when ElevenLabs is not configured.
 */

const RECORDER_TYPES = ["audio/webm", "audio/ogg", "audio/mp4"];
const MAX_RECORDING_MS = 30_000;

export function canRecord(): boolean {
  return typeof MediaRecorder !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
}

export interface Recording {
  stop: () => Promise<Blob>;
}

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mimeType = RECORDER_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
  const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
  const chunks: Blob[] = [];
  recorder.ondataavailable = (event) => chunks.push(event.data);

  const done = new Promise<Blob>((resolve) => {
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop());
      resolve(new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" }));
    };
  });
  const timeout = window.setTimeout(() => recorder.state !== "inactive" && recorder.stop(), MAX_RECORDING_MS);
  recorder.start();

  return {
    stop: () => {
      window.clearTimeout(timeout);
      if (recorder.state !== "inactive") recorder.stop();
      return done;
    },
  };
}

// --- Browser speech recognition fallback (Chrome/Edge/Safari) ------------------------------------
interface BrowserRecognition {
  lang: string;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type RecognitionConstructor = new () => BrowserRecognition;

function recognitionConstructor(): RecognitionConstructor | undefined {
  const w = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

export function canUseBrowserRecognition(): boolean {
  return recognitionConstructor() !== undefined;
}

export function listenWithBrowser(lang = "nl-BE"): { result: Promise<string>; stop: () => void } {
  const Recognition = recognitionConstructor();
  if (!Recognition) {
    return { result: Promise.reject(new Error("unsupported")), stop: () => undefined };
  }
  const recognition = new Recognition();
  recognition.lang = lang;
  recognition.interimResults = false;
  const result = new Promise<string>((resolve, reject) => {
    let text = "";
    recognition.onresult = (event) => {
      text = Array.from(event.results)
        .map((alternatives) => alternatives[0]?.transcript ?? "")
        .join(" ");
    };
    recognition.onerror = () => reject(new Error("recognition failed"));
    recognition.onend = () => resolve(text.trim());
  });
  recognition.start();
  return { result, stop: () => recognition.stop() };
}

// --- Browser text-to-speech fallback -------------------------------------------------------------
const FEMALE_HINTS = /female|vrouw|femme|ellen|colette|claire|fenna|lotte|amelie|google nederlands/i;
const MALE_HINTS = /\bmale\b|man\b|homme|xander|arthur|frank|bart|maarten/i;

function browserVoice(lang: string, kind: "female" | "male"): SpeechSynthesisVoice | undefined {
  const voices = speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2)));
  const hint = kind === "male" ? MALE_HINTS : FEMALE_HINTS;
  return voices.find((v) => hint.test(v.name)) ?? voices.find((v) => v.lang === lang) ?? voices[0];
}

/** Fallback when ElevenLabs is not configured. Browsers rarely label gender, so this is best effort. */
export function speakWithBrowser(
  text: string,
  onEnd?: () => void,
  kind: "female" | "male" = "female",
  lang = "nl-BE"
): void {
  if (typeof speechSynthesis === "undefined") {
    onEnd?.();
    return;
  }
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  const voice = browserVoice(lang, kind);
  if (voice) utterance.voice = voice;
  if (kind === "male" && (!voice || !MALE_HINTS.test(voice.name))) utterance.pitch = 0.8;
  utterance.onend = () => onEnd?.();
  utterance.onerror = () => onEnd?.();
  speechSynthesis.speak(utterance);
}

export function stopBrowserSpeech(): void {
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
}
