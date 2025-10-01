import { FormEvent, useState, useRef, useEffect } from "react";
import { z } from "zod";
import { sendUserMessage } from "@/services/user_message_input";

interface Message {
  id: string;
  text: string;
  type: "user" | "ai";
  timestamp: Date;
}

const messageSchema = z.object({
  text: z
    .string()
    .trim()
    .min(1, "Message cannot be empty")
    .max(500, "Message must be less than 500 characters"),
});

interface ChatMessageProps {
  message: Message;
}

const RAW_NOTIFY_ENDPOINT =
  (typeof import.meta !== "undefined" && (import.meta as any)?.env?.VITE_NOTIFY_ENDPOINT) ||
  "";

const RAW_BACKEND_BASE_URL =
  (typeof import.meta !== "undefined" && (import.meta as any)?.env?.VITE_BACKEND_BASE_URL) ||
  "http://localhost:8000";

const BACKEND_BASE_URL =
  typeof RAW_BACKEND_BASE_URL === "string" && RAW_BACKEND_BASE_URL.length > 0
    ? RAW_BACKEND_BASE_URL
    : "http://localhost:8000";

const sanitizeBaseUrl = (url: string) => (url.endsWith("/") ? url.slice(0, -1) : url);

const NOTIFY_ENDPOINT =
  typeof RAW_NOTIFY_ENDPOINT === "string" && RAW_NOTIFY_ENDPOINT.trim().length > 0
    ? sanitizeBaseUrl(RAW_NOTIFY_ENDPOINT.trim())
    : sanitizeBaseUrl(BACKEND_BASE_URL) + "/notificar-mensagem-ia";

const formatWebhookResponse = (data: unknown): string => {
  if (!data) {
    return "Sem resposta do servidor.";
  }

  // Novo formato: { type: "IOT", content_message: "...", friendly_message: "..." }
  if (typeof data === "object" && data !== null) {
    const obj = data as { type?: string; content_message?: string; friendly_message?: string };

    if (obj.type === "IOT" && obj.friendly_message) {
      return obj.friendly_message; // Exibe a mensagem amigável
    }

    if (obj.type === "general" && obj.content_message) {
      return obj.content_message; // Exibe mensagem geral
    }
  }

  // Caso seja array vindo do backend (formato antigo)
  if (Array.isArray(data) && data.length > 0) {
    const obj = data[0] as any;

    // IoT Commands (formato antigo)
    if (obj.IOT_command && Array.isArray(obj.IOT_command)) {
      const comandos = obj.IOT_command
        .map((cmd: any, i: number) => {
          return `Comando ${i + 1}:\n- Dispositivo: ${cmd.device ?? "?"}\n- Ação: ${cmd.action ?? "?"}\n- Parâmetro: ${cmd.parameter ?? "nenhum"}\n- Tempo: ${cmd.additional_condit ?? "0"} seg`;
        })
        .join("\n\n");

      return `Para sua mensagem "IOT":\n${comandos}`;
    }

    // Mensagem geral (formato antigo)
    if (obj.type_message === "general") {
      return `Para sua mensagem "general" - ${obj.message ?? ""}`;
    }
  }

  // Caso seja objeto no formato { type, content } (formato antigo)
  if (typeof data === "object") {
    const maybeObj = data as { type?: string; content?: unknown };

    if (maybeObj.type && maybeObj.content) {
      if (maybeObj.type === "IOT" && Array.isArray(maybeObj.content)) {
        const comandos = maybeObj.content
          .map((cmd: any, i: number) => {
            return `Comando ${i + 1}:\n- Dispositivo: ${cmd.device ?? "?"}\n- Ação: ${cmd.action ?? "?"}\n- Parâmetro: ${cmd.parameter ?? "nenhum"}\n- Tempo: ${cmd.additional_condit ?? "0"} seg`;
          })
          .join("\n\n");

        return `Para sua mensagem "IOT":\n${comandos}`;
      }

      if (maybeObj.type === "general" && typeof maybeObj.content === "string") {
        return `Para sua mensagem "general" - ${maybeObj.content}`;
      }
    }
  }

  // Fallback: mostra JSON bruto
  try {
    return JSON.stringify(data, null, 2);
  } catch {
    return "Resposta recebida do servidor.";
  }
};

const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.type === "user";
  
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div
        className={`max-w-xs md:max-w-md px-4 py-3 rounded-2xl shadow-card ${
          isUser
            ? "bg-gradient-accent text-primary-foreground ml-4"
            : "bg-gradient-card text-foreground mr-4 border border-border/50"
        }`}
      >
        <div className="flex items-start space-x-2">
          {!isUser && (
            <div className="w-2 h-2 bg-tech-blue rounded-full mt-2 animate-pulse" />
          )}
          <div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.text}
            </p>
            <span
              className={`text-xs mt-1 block ${
                isUser ? "text-primary-foreground/70" : "text-muted-foreground"
              }`}
            >
              {message.timestamp.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export const ChatInterface = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      text: "Hello! I'm your smart home AI assistant. You can ask me to control devices, check status, or help with automation.",
      type: "ai",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Efeito para rolar para a última mensagem
  useEffect(() => {
    // Um pequeno timeout garante que o DOM foi atualizado antes de rolar
    setTimeout(scrollToBottom, 100);
  }, [messages, isLoading]);

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    try {
      const { text } = messageSchema.parse({ text: inputValue });
      const trimmedText = text.trim();

      const userMessage: Message = {
        id: Date.now().toString(),
        text: trimmedText,
        type: "user",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setInputValue("");
      setIsLoading(true);

      try {
        const webhookResponse = await sendUserMessage(trimmedText);

        // Verifica se é o novo formato: { type: "IOT", content_message: {...}, friendly_message: "..." }
        let aiMessageText = formatWebhookResponse(webhookResponse);
        let command = null;

        if (
          typeof webhookResponse === "object" &&
          webhookResponse !== null &&
          "type" in webhookResponse &&
          "content_message" in webhookResponse &&
          "friendly_message" in webhookResponse
        ) {
          const responseObj = webhookResponse as {
            type: string;
            content_message: any;
            friendly_message: string;
          };

          // Exibe o friendly_message no front
          aiMessageText = responseObj.friendly_message;

          // Armazena content_message como command para log no console
          command = responseObj.content_message;
        }

        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: aiMessageText, // friendly_message exibido no front
          type: "ai",
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, aiMessage]);

        // Imprime o command no console (content_message renomeado para command)
        if (command) {
          console.log("[LOG] Command recebido:", command);
        }

        // Envia o comando para o backend
        try {
          const tipo = (webhookResponse as any)?.type ?? (command ? "IOT" : "general");
          const comandoStr =
            typeof command === "string" ? command : JSON.stringify(command ?? "");

          await fetch(NOTIFY_ENDPOINT, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              mensagem: aiMessage.text,   // texto amigável que você exibiu no chat
              comando: comandoStr,        // comando (string ou objeto serializado)
              tipo,                       // "IOT" ou "general"
            }),
          });
        } catch (notificacaoError) {
          console.error("Erro ao notificar backend:", notificacaoError);
          setError("Não foi possível notificar o backend. Tente novamente."); // mantém aviso em vermelho
        }


      } catch (serviceError) {
        console.error("Failed to reach the automation service. Please try again.");
      } finally {
        setIsLoading(false);
      }
    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.issues[0].message);
      } else {
        setError("Failed to send message. Please try again.");
      }
    }
  };

  return (
    <div className="bg-gradient-card rounded-2xl shadow-card border border-border/50 h-96 flex flex-col">
      {/* Chat Header */}
      <div className="p-4 border-b border-border/50">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 bg-tech-blue rounded-full animate-pulse" />
          <h3 className="font-semibold text-foreground">AI Assistant</h3>
          <span className="text-xs text-muted-foreground">Online</span>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}

        {isLoading && (
          <div className="flex justify-start mb-4">
            <div className="bg-gradient-card text-foreground border border-border/50 max-w-xs md:max-w-md px-4 py-3 rounded-2xl shadow-card mr-4">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-tech-blue rounded-full animate-pulse" />
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-100" />
                  <div className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce delay-200" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Elemento invisível para marcar o fim do chat e ajudar no scroll */}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="p-4 border-t border-border/50">
        {error && (
          <div className="mb-2 text-sm text-destructive bg-destructive/10 px-3 py-1 rounded">
            {error}
          </div>
        )}

        <div className="flex space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            placeholder="Type your command..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-dark-surface border border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
            maxLength={500}
          />
          <button
            type="submit"
            disabled={isLoading || !inputValue.trim()}
            className="px-6 py-2 bg-gradient-accent text-primary-foreground rounded-lg font-medium hover:bg-gradient-hover transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-card hover:shadow-hover"
          >
            Send
          </button>
        </div>

        <div className="flex justify-between items-center mt-2 text-xs text-muted-foreground">
          <span>Press Enter to send</span>
          <span>{inputValue.length}/500</span>
        </div>
      </form>
    </div>
  );
};