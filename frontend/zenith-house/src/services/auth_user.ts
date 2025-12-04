const backendBaseUrl = import.meta.env.VITE_BACKEND_BASE_URL as string;
if (!backendBaseUrl) {
  throw new Error("VITE_BACKEND_BASE_URL não configurada");
}

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
const AUTH_CHECK_URL = `${backendBaseUrl}/auth_check_user`;

export async function checkAuth(): Promise<AuthCheckResponse> {
  try {
    // Chamada ao backend confiando no cookie HttpOnly enviado pelo backend
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
