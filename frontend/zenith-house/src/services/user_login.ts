import { BACKEND_BASE_URL } from "./backend_config";
import { WEBHOOK_BASE_URL } from "./backend_config";


export interface LoginResponse {
  status: "success" | "error" | string;
  message?: string;
  session_id?: string;
  user?: {
    id: string;
    email: string;
  };
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  try {
    const response = await fetch(`${WEBHOOK_BASE_URL}/login_user_webhook`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // ⚠️ envia e recebe cookies automaticamente
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const errText = await response.text();
      return { status: "error", message: errText || `HTTP ${response.status}` };
    }

    const data = (await response.json()) as LoginResponse;
    console.log("[Login Response]", data);
    return data;
  } catch (err: any) {
    return { status: "error", message: err.message || "Network error" };
  }
}
