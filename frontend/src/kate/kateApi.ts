import { ApiError, apiClient } from "../api/client";

export interface KateStatus {
  llm: "mock" | "gemini";
  voice: boolean;
  speech_recognition: boolean;
}

export interface KateAction {
  type: "none" | "transfer" | "advisor_handoff";
  to_name: string | null;
  amount: string | null;
  description: string | null;
  summary: string | null;
}

export interface KateChatResponse {
  reply: string;
  mode: "normal" | "guidance";
  action: KateAction;
}

export interface ChatTurn {
  role: "user" | "kate";
  text: string;
}

export const MAX_HISTORY = 10;

/** Pre-fill for the normal transfer screen; the customer checks and confirms there. */
export function transferLink(action: KateAction): string {
  const params = new URLSearchParams();
  if (action.to_name) params.set("to_name", action.to_name);
  if (action.amount) params.set("amount", action.amount);
  if (action.description) params.set("description", action.description);
  return `/transfer?${params.toString()}`;
}

export type VoiceKind = "female" | "male";

export interface KateVoice {
  voice: VoiceKind;
  default_voice: VoiceKind;
  available: VoiceKind[];
}

export function getKateVoice(signal?: AbortSignal): Promise<KateVoice> {
  return apiClient.get<KateVoice>("/kate/voice", signal);
}

export function setKateVoice(voice: VoiceKind): Promise<KateVoice> {
  return apiClient.post<KateVoice>("/kate/voice", { voice });
}

export function getKateStatus(signal?: AbortSignal): Promise<KateStatus> {
  return apiClient.get<KateStatus>("/kate/status", signal);
}

export function sendKateMessage(message: string, history: ChatTurn[]): Promise<KateChatResponse> {
  return apiClient.post<KateChatResponse>("/kate/chat", {
    message,
    history: history.slice(-MAX_HISTORY),
  });
}

export async function transcribe(audio: Blob): Promise<string> {
  const response = await apiClient.post<{ text: string }>("/kate/transcribe", {
    audio_base64: await blobToBase64(audio),
    mime_type: audio.type.split(";")[0],
  });
  return response.text;
}

/** Kate's voice as MP3 (not JSON, so this bypasses the JSON client). */
export async function fetchSpeech(text: string): Promise<Blob> {
  const response = await fetch("/api/v1/kate/speech", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", Accept: "audio/mpeg" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Kate's stem is niet beschikbaar.");
  }
  return response.blob();
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(reader.error ?? new Error("read failed"));
    reader.readAsDataURL(blob);
  });
}
