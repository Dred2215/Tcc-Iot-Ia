export interface WebhookResponse {
  type: string;
  content_message: string;
  friendly_message: string;
}

const WEBHOOK_URL = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/test-message";

export async function sendUserMessage(message: string): Promise<WebhookResponse> {
  try {
    const res = await fetch(WEBHOOK_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ comando: message }),
    });

    if (!res.ok) {
      throw new Error(`Erro na requisição: ${res.statusText}`);
    }

    const data = await res.json();
    
    // ✅ Log para ver o formato exato da resposta
    console.log("[DEBUG] Resposta bruta da IA:", data);
    
    return data;
  } catch (error) {
    console.error("Erro ao enviar mensagem:", error);
    throw error;
  }
}