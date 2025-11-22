export interface AuthCheckResponse {
  status: "success" | "error" | "valid" | string;
  message?: string;
  user?: {
    id: string;
    email: string;
  };
  data?: any; // para capturar retorno do backend
}

const BACKEND_BASE_URL = (
  (import.meta.env.VITE_BACKEND_BASE_URL as string | undefined)?.trim() ||
  "http://localhost:8000"
).replace(/\/$/, "");

// Novo endpoint local do backend FastAPI
const AUTH_CHECK_URL = `${BACKEND_BASE_URL}/auth_check_user`;

export async function checkAuth(): Promise<AuthCheckResponse> {
  try {
    // ⚠️ Agora não pegamos nada do localStorage.
    // O cookie HttpOnly é enviado automaticamente.
    const response = await fetch(AUTH_CHECK_URL, {
      method: "GET",
      credentials: "include", // 🔒 envia o cookie session_id
    });

    if (!response.ok) {
      console.warn("[AuthCheck] HTTP error:", response.status);
      return { status: "error", message: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as AuthCheckResponse;
    console.log("[AuthCheck]", data);

    // Caso o backend use "valid" como status:
    if (data.status === "valid" || data.status === "success") {
      return { status: "success", user: data.user, data };
    }

    return { status: "error", message: "Session invalid or expired" };
  } catch (err: any) {
    console.error("[AuthCheck Error]", err);
    return { status: "error", message: err.message || "Network error" };
  }
}
