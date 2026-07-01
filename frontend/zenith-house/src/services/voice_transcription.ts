import { BACKEND_BASE_URL } from "./backend_config";

const VOICE_TRANSCRIBE_URL = `${BACKEND_BASE_URL}/voice_transcribe`;

export interface TranscribeResult {
  status: "success" | "error" | string;
  text?: string;
  detail?: string;
}

// Envia o áudio gravado (Blob do MediaRecorder) ao backend para transcrição.
export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "gravacao.webm");

  const response = await fetch(VOICE_TRANSCRIBE_URL, {
    method: "POST",
    credentials: "include",
    body: formData,
  });

  const result = (await response.json().catch(() => ({}))) as TranscribeResult;

  if (!response.ok) {
    throw new Error(result.detail || `Falha ao transcrever áudio: ${response.status} ${response.statusText}`.trim());
  }

  if (!result.text) {
    throw new Error("Nenhum texto retornado pela transcrição.");
  }

  return result.text;
}
