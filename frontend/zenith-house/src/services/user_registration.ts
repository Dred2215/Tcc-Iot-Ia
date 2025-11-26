export interface RegisterUserInput {
  fullName: string;
  email: string;
  password: string;
  phone?: string;
}

export interface RegisterWebhookPayload {
  event: "user_registration";
  timestamp: string;
  user: {
    full_name: string;
    email: string;
    phone?: string | null;
  };
  credentials: {
    password: string;
  };
  meta: {
    source: string;
    version: string;
  };
}

export interface RegisterWebhookResponse {
  status: "success" | "error" | string;
  message?: string;
  userId?: string;
  data?: unknown;
}

export interface RegisterUserResult {
  requestPayload: RegisterWebhookPayload;
  responsePayload: RegisterWebhookResponse;
}

<<<<<<< HEAD
const DEFAULT_WEBHOOK_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook/register-user";
const envRegisterWebhook =
  typeof import.meta !== "undefined"
    ? ((import.meta as any)?.env?.VITE_REGISTER_WEBHOOK_URL as string | undefined)
    : undefined;
const REGISTER_WEBHOOK_URL = (envRegisterWebhook?.trim() || DEFAULT_WEBHOOK_URL).replace(/\/$/, "");
=======
const DEFAULT_REGISTER_WEBHOOK_URL = "https://tcc-iot-n8n.dlivfa.easypanel.host/webhook/register-user";

const REGISTER_WEBHOOK_URL =
  (import.meta.env.VITE_REGISTER_WEBHOOK_URL as string | undefined)?.trim() || DEFAULT_REGISTER_WEBHOOK_URL;
>>>>>>> origin/main

export const buildRegisterPayload = (input: RegisterUserInput): RegisterWebhookPayload => ({
  event: "user_registration",
  timestamp: new Date().toISOString(),
  user: {
    full_name: input.fullName,
    email: input.email,
    phone: input.phone ?? null,
  },
  credentials: {
    password: input.password,
  },
  meta: {
    source: "zenith-house-frontend",
    version: "1.0.0",
  },
});

export async function registerUser(input: RegisterUserInput): Promise<RegisterUserResult> {
  if (!REGISTER_WEBHOOK_URL) {
    throw new Error("REGISTER_WEBHOOK_URL (VITE_REGISTER_WEBHOOK_URL) is not defined");
  }

  const requestPayload = buildRegisterPayload(input);

  const response = await fetch(REGISTER_WEBHOOK_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestPayload),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(`Falha ao registrar usuario: ${response.status} ${response.statusText} ${errorText}`.trim());
  }

  const responsePayload = (await response.json().catch(() => ({ status: "error", message: "Resposta JSON invalida" }))) as RegisterWebhookResponse;

  return {
    requestPayload,
    responsePayload,
  };
}
