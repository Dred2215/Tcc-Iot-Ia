const DEFAULT_WEBHOOK_BASE_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook";
const DEFAULT_WEBHOOK_TEST_BASE_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook-test";

/**
 * Reads a Vite env var, validates it and normalizes the URL.
 */
function getEnvUrl(key: string, fallback?: string): string {
  const raw = (
    typeof import.meta !== "undefined"
      ? ((import.meta as any).env?.[key] as string | undefined)
      : undefined
  )?.trim();

  if (!raw) {
    if (fallback) {
      console.warn(`[Env] ${key} nao configurada. Usando fallback padrao.`);
      return fallback.replace(/\/$/, "");
    }
    throw new Error(`Variavel de ambiente ${key} nao configurada.`);
  }

  // Remove trailing slash to keep URL concatenations consistent
  return raw.replace(/\/$/, "");
}

// ------------------------------
// Final exports
// ------------------------------
export const BACKEND_BASE_URL = getEnvUrl("VITE_BACKEND_BASE_URL");
export const WEBHOOK_BASE_URL = getEnvUrl("VITE_WEBHOOK_BASE_URL", DEFAULT_WEBHOOK_BASE_URL);
export const WEBHOOK_TEST_BASE_URL = getEnvUrl(
  "VITE_WEBHOOK_TEST_BASE_URL",
  DEFAULT_WEBHOOK_TEST_BASE_URL
);
