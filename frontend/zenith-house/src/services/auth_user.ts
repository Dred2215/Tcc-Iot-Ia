export interface AuthCheckResponse {
  status: "success" | "error" | string;
  message?: string;
  user?: {
    id: string;
    email: string;
  };
}

const AUTH_CHECK_URL =
  "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/auth_check_user";

export async function checkAuth(): Promise<AuthCheckResponse> {
  const sessionId = localStorage.getItem("session_id");

  if (!sessionId) {
    return { status: "error", message: "No session_id found in localStorage" };
  }

  try {
    const url = new URL(AUTH_CHECK_URL);
    url.searchParams.append("session_id", sessionId);

    const response = await fetch(url.toString(), {
      method: "GET",
    });

    if (!response.ok) {
      return { status: "error", message: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as AuthCheckResponse;

    // 👇 debug
    console.log("[Auth Check Response]", data);

    return data;
  } catch (err: any) {
    console.error("[Auth Check Error]", err);
    return { status: "error", message: err.message || "Network error" };
  }
}
