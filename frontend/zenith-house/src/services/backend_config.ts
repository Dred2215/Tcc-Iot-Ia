const DEFAULT_LOCAL_BACKEND = "http://localhost:8000";
const DEV_SERVER_PORTS = new Set(["5173", "4173", "4174", "3000"]);

const trimTrailingSlashes = (value: string) => value.replace(/\/+$/, "");

const readEnv = (key: string): string | undefined => {
  const raw = (
    typeof import.meta !== "undefined" ? ((import.meta as any).env?.[key] as string | undefined) : undefined
  )?.trim();
  return raw && raw.length > 0 ? raw : undefined;
};

const resolveBackendBaseFromWindow = (): string | undefined => {
  if (typeof window === "undefined" || !window.location) return undefined;
  const { protocol, hostname, port } = window.location;
  if (!protocol || !hostname) return undefined;

  const desiredPort = DEV_SERVER_PORTS.has(port ?? "")
    ? readEnv("VITE_LOCAL_BACKEND_PORT") ?? "8000"
    : port;
  const portSegment = desiredPort ? `:${desiredPort}` : "";
  return `${protocol}//${hostname}${portSegment}`;
};

const rawBackendBase =
  readEnv("VITE_BACKEND_BASE_URL") ??
  resolveBackendBaseFromWindow() ??
  DEFAULT_LOCAL_BACKEND;

export const BACKEND_BASE_URL = trimTrailingSlashes(rawBackendBase);
