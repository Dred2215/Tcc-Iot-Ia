import { BACKEND_BASE_URL } from "./backend_config";
import { WEBHOOK_BASE_URL } from "./backend_config";

export interface WebhookResponseNormalized {
  comando: string;
  respostaIA: string;
  device?: string | null;
  action?: string | null;
  raw?: any;
}

const WEBHOOK_URL = `${WEBHOOK_BASE_URL}/message_input`;

const getContentMessageText = (content: unknown): string | null => {
  if (!content) return null;
  if (typeof content === "string") return content;
  if (typeof content === "object") {
    const { message, friendly_message, text } = content as Record<string, unknown>;
    if (typeof message === "string") return message;
    if (typeof friendly_message === "string") return friendly_message;
    if (typeof text === "string") return text;
  }
  return null;
};

export async function sendUserMessage(message: string): Promise<WebhookResponseNormalized> {
  try {
    const res = await fetch(WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ comando: message }),
    });

    if (!res.ok) {
      throw new Error(`Erro na requisição: ${res.statusText}`);
    }

    const rawText = await res.text();
    let data: any = {};

    if (rawText.trim().length === 0) {
      console.warn("[DEBUG] Webhook retornou resposta vazia.");
    } else {
      try {
        data = JSON.parse(rawText);
      } catch (jsonError) {
        console.error("Erro ao converter resposta em JSON:", jsonError);
        throw new Error("Resposta inválida do servidor.");
      }
    }

    console.log("[DEBUG] Resposta bruta da IA:", data);

    let respostaIA = "";
    let device: string | null = null;
    let action: string | null = null;

    // 🚀 Trata o formato que vem como array
    if (Array.isArray(data) && data.length > 0) {
      const obj = data[0];
      const contentText = getContentMessageText(obj.content_message);
      respostaIA = contentText || obj.IOT_message || obj.friendly_message || "Comando processado.";

      // 📦 Se o retorno usa content_message
      if (obj.content_message) {
        device = (obj.content_message as any).device || null;
        action = (obj.content_message as any).action || null;
      }

      // 📦 Ou, se usa IOT_command (outro formato possível)
      if (obj.IOT_command && Array.isArray(obj.IOT_command) && obj.IOT_command.length > 0) {
        const cmd = obj.IOT_command[0];
        device = cmd.device || device;
        action = cmd.action || action;
      }
    }

    // 🚀 Trata formato de objeto direto
    else if (typeof data === "object" && data !== null) {
      const contentText = getContentMessageText((data as any).content_message);
      respostaIA = contentText || (data as any).IOT_message || (data as any).friendly_message || "Comando processado.";

      if ((data as any).content_message) {
        device = (data as any).content_message.device || null;
        action = (data as any).content_message.action || null;
      }

      if ((data as any).IOT_command && Array.isArray((data as any).IOT_command)) {
        const cmd = (data as any).IOT_command[0];
        device = cmd.device || device;
        action = cmd.action || action;
      }
    }

    return {
      comando: message,
      respostaIA,
      device,
      action,
      raw: data,
    };
  } catch (error) {
    console.error("Erro ao enviar mensagem:", error);
    throw error;
  }
}
