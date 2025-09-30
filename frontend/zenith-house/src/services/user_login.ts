export interface LoginResponse {
  status: "success" | "error" | string;
  message?: string;
  session_id?: string;
  user?: {
    id: string;
    email: string;
  };
}

const LOGIN_WEBHOOK_URL =
  "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/login_user_webhook";

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  try {
    const url = new URL(LOGIN_WEBHOOK_URL);
    url.searchParams.append("email", email);
    url.searchParams.append("password", password);

    const response = await fetch(url.toString(), {
      method: "GET",
    });

    if (!response.ok) {
      return { status: "error", message: `HTTP ${response.status}` };
    }

    const data = (await response.json()) as LoginResponse;
    console.log("[Login Response]", data);

    return data;
  } catch (err: any) {
    return { status: "error", message: err.message || "Network error" };
  }
}
