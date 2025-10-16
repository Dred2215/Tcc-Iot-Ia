export interface LoginResponse {
  status: "success" | "error" | string;
  message?: string;
  session_id?: string;
  user?: {
    id: string;
    email: string;
  };
}



const LOGIN_WEBHOOK_URL = import.meta.env.VITE_LOGIN_WEBHOOK_URL;


export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  try {
    const response = await fetch("http://localhost:8000/login_user", {
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
