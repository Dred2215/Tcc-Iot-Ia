export interface WebhookResponseNormalized {
  comando: string;
  respostaIA: string;
  device?: string | null;
  action?: string | null;
  raw?: any;
}

const WEBHOOK_URL = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/test-message";

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

    const data = await res.json();
    console.log("[DEBUG] Resposta bruta da IA:", data);

    let respostaIA = "";
    let device: string | null = null;
    let action: string | null = null;

    // 🚀 Trata o formato que vem como array
    if (Array.isArray(data) && data.length > 0) {
      const obj = data[0];
      respostaIA = obj.IOT_message || obj.friendly_message || "Comando processado.";

      // 📦 Se o retorno usa content_message
      if (obj.content_message) {
        device = obj.content_message.device || null;
        action = obj.content_message.action || null;
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
      respostaIA = (data as any).IOT_message || (data as any).friendly_message || "Comando processado.";

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
