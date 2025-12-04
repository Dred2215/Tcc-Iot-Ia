import { BACKEND_BASE_URL } from "@/services/backend_config";

const PROTOCOL_REGEX = /^[a-zA-Z][a-zA-Z\d+\-.]*:\/\//;

const readEnv = (key: string): string | undefined => {
  const raw = (
    typeof import.meta !== "undefined" ? ((import.meta as any).env?.[key] as string | undefined) : undefined
  )?.trim();

  return raw ? raw : undefined;
};

const shouldUseSecure = () =>
  typeof window !== "undefined" && typeof window.location !== "undefined"
    ? window.location.protocol === "https:"
    : true;

const normalizeToUrl = (raw?: string): URL | null => {
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;

  try {
    const direct = new URL(trimmed);
    return direct;
  } catch {
    const withProtocol = PROTOCOL_REGEX.test(trimmed) ? trimmed : `https://${trimmed}`;
    try {
      return new URL(withProtocol);
    } catch (err) {
      console.warn(`[VoiceWS] Invalid URL value "${trimmed}":`, err);
      return null;
    }
  }
};

const normalizeProtocol = (url: URL) => {
  if (url.protocol === "ws:" || url.protocol === "wss:") {
    if (url.protocol === "ws:" && shouldUseSecure()) {
      url.protocol = "wss:";
    }
    return;
  }

  if (url.protocol === "http:" || url.protocol === "https:") {
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return;
  }

  url.protocol = shouldUseSecure() ? "wss:" : "ws:";
};

const applyPort = (url: URL) => {
  if (url.port) return;
  const desiredPort = readEnv("VITE_VOICE_WS_PORT");
  if (desiredPort) {
    url.port = desiredPort;
  }
};

const urlToBaseString = (url: URL): string => {
  const pathname = url.pathname.replace(/\/$/, "");
  const origin = url.origin;
  return pathname && pathname !== "/" ? `${origin}${pathname}` : origin;
};

const buildFromCandidate = (raw?: string, applyPortFromEnv = true): string | null => {
  const candidate = normalizeToUrl(raw);
  if (!candidate) return null;
  normalizeProtocol(candidate);
  if (applyPortFromEnv) applyPort(candidate);
  return urlToBaseString(candidate);
};

const buildFromWindow = (): string | null => {
  if (typeof window === "undefined" || typeof window.location === "undefined") {
    return null;
  }
  const { protocol, host } = window.location;
  const wsProtocol = protocol === "https:" ? "wss" : "ws";
  return `${wsProtocol}://${host}`;
};

export const resolveVoiceWsBase = (): string => {
  // Se VITE_VOICE_WS_BASE vier explícito, não aplicamos porta via env (assume que já está correta)
  const explicit = buildFromCandidate(readEnv("VITE_VOICE_WS_BASE"), false);
  if (explicit) return explicit;

  const backendBase = buildFromCandidate(BACKEND_BASE_URL);
  if (backendBase) return backendBase;

  const browserBase = buildFromWindow();
  if (browserBase) return browserBase;

  throw new Error("Unable to determine the voice WebSocket endpoint.");
};

export const buildVoiceWsUrl = (path: string): string => {
  const base = resolveVoiceWsBase().replace(/\/$/, "");
  const finalPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${finalPath}`;
};
