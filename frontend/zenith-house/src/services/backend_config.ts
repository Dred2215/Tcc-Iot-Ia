const DEFAULT_WEBHOOK_BASE_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook";
const DEFAULT_WEBHOOK_TEST_BASE_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook-test";
const DEFAULT_LOCAL_BACKEND = "http://localhost:8000";
const DEV_SERVER_PORTS = new Set(["5173", "4173", "4174", "3000"]);

const trimTrailingSlashes = (value: string) => value.replace(/\/+$/, "");

const readEnv = (key: string): string | undefined => {
  const raw = (
    typeof import.meta !== "undefined" ? ((import.meta as any).env?.[key] as string | undefined) : undefined
  )?.trim();
  return raw && raw.length > 0 ? raw : undefined;
};

const getEnvUrl = (key: string, fallback?: string): string => {
  const value = readEnv(key) ?? fallback;
  if (!value) {
    throw new Error(`Variavel de ambiente ${key} nao configurada.`);
  }
  return trimTrailingSlashes(value);
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
export const WEBHOOK_BASE_URL = getEnvUrl("VITE_WEBHOOK_BASE_URL", DEFAULT_WEBHOOK_BASE_URL);
export const WEBHOOK_TEST_BASE_URL = getEnvUrl("VITE_WEBHOOK_TEST_BASE_URL", DEFAULT_WEBHOOK_TEST_BASE_URL);
