/**
 * Lê uma variável do Vite, valida e normaliza a URL.
 */
function getEnvUrl(key: string): string {
  const raw = (
    typeof import.meta !== "undefined"
      ? ((import.meta as any).env?.[key] as string | undefined)
      : undefined
  )?.trim();

  if (!raw) {
    throw new Error(`Variável de ambiente ${key} não configurada.`);
  }

  // Remove barra final
  return raw.replace(/\/$/, "");
}

// ------------------------------
// Exportações finais (limpas)
// ------------------------------
export const BACKEND_BASE_URL = getEnvUrl("VITE_BACKEND_BASE_URL");
export const WEBHOOK_BASE_URL = getEnvUrl("VITE_WEBHOOK_BASE_URL");
export const WEBHOOK_TEST_BASE_URL = getEnvUrl("VITE_WEBHOOK_TEST_BASE_URL");
