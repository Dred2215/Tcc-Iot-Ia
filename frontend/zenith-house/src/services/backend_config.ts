const rawBackendBaseUrl = (
  typeof import.meta !== "undefined" ? ((import.meta as any).env?.VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE as string | undefined) : undefined
)?.trim();

if (!rawBackendBaseUrl) {
  throw new Error("VITE_BACKEND_BASE_URL is not configurada para o frontend.");
}

export const BACKEND_BASE_URL = rawBackendBaseUrl.replace(/\/$/, "");
