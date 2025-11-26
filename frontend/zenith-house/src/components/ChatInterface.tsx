import { FormEvent, useState, useRef, useEffect } from "react";
import { z } from "zod";
import { sendUserMessage } from "@/services/user_message_input_chat";
import { BACKEND_BASE_URL } from "@/services/backend_config";

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

const NOTIFY_ENDPOINT = `${BACKEND_BASE_URL}/notificar-mensagem-ia`;


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
          {!isUser && <div className="w-2 h-2 bg-tech-blue rounded-full mt-2 animate-pulse" />}
          <div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.text}</p>
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

  useEffect(() => {
    setTimeout(scrollToBottom, 100);
  }, [messages, isLoading]);

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError("");

    try {
      const { text } = messageSchema.parse({ text: inputValue });
      const trimmedText = text.trim();

      // 💬 Adiciona mensagem do usuário no chat
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
        // 🚀 Envia comando para o backend (/message_input) e recebe payload normalizado
        const response = await sendUserMessage(trimmedText);
        console.log("[DEBUG] Payload normalizado:", response);

        // 💬 Mostra resposta da IA no chat
        const aiMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: response.respostaIA || "Sem resposta da IA.",
          type: "ai",
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, aiMessage]);

        // 🧩 Monta payload completo para backend FastAPI
        const backendPayload = {
          user_message: response.comando,    // comando do usuário
          mensagem: response.respostaIA,     // resposta da IA
          comando: response.raw,             // estrutura bruta completa
          tipo: response.device ? "IOT" : "general",
          device: response.device,           // nome do dispositivo
          action: response.action,           // ação executada
        };

        console.log("[DEBUG] Enviando para backend:", backendPayload);

        // 🔗 Envia notificação ao backend
        const backendResponse = await fetch(NOTIFY_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(backendPayload),
        });

        const backendText = await backendResponse.text();
        let backendResult: any = null;

        if (backendText) {
          try {
            backendResult = JSON.parse(backendText);
          } catch (parseError) {
            console.error("[DEBUG] Falha ao converter resposta do backend:", parseError, backendText);
          }
        }

        if (!backendResponse.ok) {
          throw new Error(backendResult?.detail || "Falha ao notificar backend.");
        }

        const feedbacks = Array.isArray(backendResult?.iot_feedback) ? backendResult.iot_feedback : [];
        const timestampBase = Date.now();
        const feedbackMessages: Message[] = feedbacks
          .filter((item: any) => typeof item?.message === "string" && item.message.trim().length > 0)
          .map((item: any, index: number) => ({
            id: `${timestampBase}-iot-${index}`,
            text: item.message.trim(),
            type: "ai",
            timestamp: new Date(),
          }));

        if (feedbackMessages.length > 0) {
          console.log("[DEBUG] Feedback IoT recebido:", feedbackMessages);
          setMessages((prev) => [...prev, ...feedbackMessages]);
        }

      } catch (notificacaoError) {
        console.error("Erro ao processar mensagem:", notificacaoError);
        setError("Não foi possível processar a mensagem. Tente novamente.");
      } finally {
        setIsLoading(false);
      }

    } catch (err) {
      if (err instanceof z.ZodError) {
        setError(err.issues[0].message);
      } else {
        setError("Falha ao enviar mensagem. Tente novamente.");
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

      {/* Messages */}
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
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
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
