import { BACKEND_BASE_URL } from "./backend_config";

export interface AuthCheckResponse {
  status: "success" | "error" | "valid" | string;
  message?: string;
  user?: {
    id: string;
    email: string;
  };
  data?: any; // para capturar retorno do backend
}

// Endpoint publico do backend FastAPI para verificacao de sessao (backend faz proxy para o webhook)
const AUTH_CHECK_URL = `${BACKEND_BASE_URL}/auth_check_user`;

export async function checkAuth(): Promise<AuthCheckResponse> {
  try {
    // Para este teste, apenas chamamos o backend (ping) e confiamos no status HTTP
    const response = await fetch(AUTH_CHECK_URL, {
      method: "GET",
      credentials: "include",
    });

    if (!response.ok) {
      console.warn("[AuthCheck] HTTP error:", response.status);
      return { status: "error", message: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as AuthCheckResponse;
    console.log("[AuthCheck]", data);

    return { status: "success", user: data.user, data };
  } catch (err: any) {
    console.error("[AuthCheck Error]", err);
    return { status: "error", message: err.message || "Network error" };
  }
}
