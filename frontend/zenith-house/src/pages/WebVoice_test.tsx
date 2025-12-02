import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Mic, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";

type WebhookPayload =
  | {
      type?: string;
      friendly_message?: string;
      content_message?:
        | string
        | {
            friendly_message?: string;
            message?: string;
            text?: string;
            status?: string;
          };
      IOT_message?: string;
      message?: string;
    }
  | string;

const extractWebhookMessage = (payload: WebhookPayload): string => {
  if (!payload) return "";
  if (typeof payload === "string") return payload;

  const fromContent = payload.content_message;
  if (fromContent) {
    if (typeof fromContent === "string") return fromContent;
    if (typeof fromContent === "object") {
      if (typeof fromContent.friendly_message === "string") return fromContent.friendly_message;
      if (typeof fromContent.message === "string") return fromContent.message;
      if (typeof fromContent.text === "string") return fromContent.text;
      if (typeof fromContent.status === "string") return fromContent.status;
    }
  }

  if (typeof payload.friendly_message === "string") return payload.friendly_message;
  if (typeof payload.IOT_message === "string") return payload.IOT_message;
  if (typeof payload.message === "string") return payload.message;

  return "";
};

const safeJsonParse = (text: string): WebhookPayload | null => {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
};

const formatVoiceServerMessage = (raw: string): string => {
  if (!raw) return "";

  const trimmed = raw.trim();
  const direct = safeJsonParse(trimmed);
  if (direct) {
    const msg = extractWebhookMessage(direct);
    if (msg) return msg;
  }

  const jsonMatch = trimmed.match(/\{.*\}$/s);
  if (jsonMatch) {
    const parsedTail = safeJsonParse(jsonMatch[0]);
    if (parsedTail) {
      const msg = extractWebhookMessage(parsedTail);
      if (msg) return msg;
    }
  }

  return trimmed;
};

const Voice_STT_Test = () => {
  const navigate = useNavigate();


  

  // =====================================================
  // 🎛️ Estados
  // =====================================================
  const [isListening, setIsListening] = useState(false);
  const [recognizedText, setRecognizedText] = useState("");
  const [statusMessage, setStatusMessage] = useState("Inicializando...");

  // =====================================================
  // 🔗 Referências
  // =====================================================
  const recognitionRef = useRef<any | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const isCommandMode = useRef(false);
  const commandText = useRef("");
  const commandTimer = useRef<any>(null);

  const WS_BASE_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8008";

  // ⏱️ Timer de 10s após detectar "bob"
  const commandStartTimer = () => {
    clearTimeout(commandTimer.current);
    commandTimer.current = setTimeout(() => {
      console.log("⏰ Tempo limite atingido — enviando comando final.");
      finalizeCommand();
    }, 10000); // 10 segundos
  };

  // 📨 Finaliza e envia o comando ao servidor
  const finalizeCommand = () => {
    clearTimeout(commandTimer.current);

    if (commandText.current.trim() !== "") {
      sendVoiceCommand(commandText.current.trim());
    } else {
      console.warn("⚠️ Nenhum comando detectado.");
    }

    // Reset
    isCommandMode.current = false;
    commandText.current = "";
    const recognition = recognitionRef.current;
    if (recognition) recognition.stop();
  };


  // =====================================================
  // 🧠 Inicializa reconhecimento e WebSocket único
  // =====================================================
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Seu navegador não suporta reconhecimento de voz (Web Speech API).");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "pt-BR";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
      setIsListening(true);
      console.log("🎙️ Reconhecimento iniciado.");
      setStatusMessage("🎧 Escutando... diga 'bob' para ativar.");
    };

    recognition.onend = () => {
      setIsListening(false);
      console.log("🛑 Reconhecimento finalizado.");
      // Reinicia automaticamente a escuta
      setTimeout(() => {
        recognition.start();
      }, 800);
    };

    recognition.onerror = (event: any) => {
      console.error("⚠️ Erro no reconhecimento:", event.error);
      setStatusMessage("❌ Erro no reconhecimento de voz.");
    };

    recognition.onresult = (event: any) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        text += event.results[i][0].transcript;
      }

      text = text.trim().toLowerCase();
      setRecognizedText(text);

      // ================================
      // 🔎 Detecção da hotword "bob"
      // ================================
      if (text.includes("bob") && !isCommandMode.current) {
        console.log("🚀 Hotword detectada: bob");
        setStatusMessage("🟢 Hotword detectada — aguardando comando...");
        isCommandMode.current = true; // ativa modo comando
        commandText.current = ""; // zera o buffer
        commandStartTimer();
      }

      // Se já estamos no modo comando, acumular texto
      if (isCommandMode.current) {
        commandText.current = text;

        // Se resultado final detectado antes do timeout
        const lastResult = event.results[event.results.length - 1];
        if (lastResult.isFinal) {
          console.log("✅ Fala final detectada — enviando antes do timeout.");
          finalizeCommand();
        }
      }
    };


    recognitionRef.current = recognition;
    connectSocket();
    recognition.start();

    return () => {
      recognition.stop();
      socketRef.current?.close();
    };
  }, []);

  // =====================================================
  // 🔌 WebSocket Único
  // =====================================================
  const connectSocket = () => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws-hotword`);

    ws.onopen = () => {
      console.log("👂 [HOTWORD] Conectado ao servidor");
      setStatusMessage("🎧 Detector ativo — diga 'bob' para iniciar comando.");
    };

    ws.onmessage = (e) => {
      console.log("📩 [SERVER]", e.data);
      setStatusMessage(e.data);
    };

    ws.onclose = () => {
      console.log("🔌 [HOTWORD] Conexão encerrada — aguardando próxima hotword.");
      setStatusMessage("🕓 Aguardando nova hotword...");
      socketRef.current = null; // limpa o socket
    };


    ws.onerror = (e) => {
      console.error("⚠️ [HOTWORD] Erro", e);
      setStatusMessage("❌ Erro na conexão com o servidor.");
    };

    socketRef.current = ws;
  };

  // =====================================================
  // 🔌 WebSocket de Comando (VOICE)
  // =====================================================
  const sendVoiceCommand = (text: string) => {
    const ws = new WebSocket(`${WS_BASE_URL}/ws-voice`);

    ws.onopen = () => {
      console.log("🎤 [VOICE] Conectado ao servidor.");
      ws.send(text);
      console.log("📤 [VOICE] Comando enviado:", text);
      setStatusMessage("📨 Comando enviado ao servidor.");
    };

    ws.onmessage = (e: MessageEvent<string>) => {
      console.log("🤖 [SERVER VOICE]", e.data);
      const formatted = formatVoiceServerMessage(e.data);
      setStatusMessage(formatted || e.data);
    };

    ws.onclose = () => {
      console.log("🔌 [VOICE] Conexão encerrada.");
    };

    ws.onerror = (e) => {
      console.error("⚠️ [VOICE] Erro:", e);
      setStatusMessage("❌ Erro ao enviar comando ao servidor.");
    };
  };


  // // =====================================================
  // // 📤 Envia apenas a hotword
  // // =====================================================
  // const sendHotword = (text: string) => {
  //   const ws = socketRef.current;
  //   if (ws && ws.readyState === WebSocket.OPEN) {
  //     ws.send(text);
  //     console.log("📤 [CLIENTE] Enviado:", text);
  //   } else {
  //     console.warn("⚠️ WebSocket não está aberto.");
  //     setStatusMessage("⚠️ Não foi possível enviar a hotword.");
  //   }
  // };

  // =====================================================
  // 🎨 Interface
  // =====================================================
  const buttonState = isListening ? "recording" : "idle";

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        {/* Botão Voltar */}
        <button
          onClick={() => navigate("/")}
          className="inline-flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8"
        >
          <ArrowLeft size={20} />
          <span>Back to Home</span>
        </button>

        {/* Cabeçalho */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Voice Hotword Test
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            A escuta começa automaticamente. Diga “bob” e a conexão será encerrada após o envio.
          </p>
        </div>

        {/* Status */}
        <div className="text-center mb-6">
          <p className="text-sm text-tech-blue">{statusMessage}</p>
        </div>

        {/* Texto reconhecido */}
        <div className="flex flex-col items-center space-y-4 mb-10">
          <textarea
            readOnly
            value={recognizedText}
            className="w-96 h-40 p-4 rounded-lg border border-border/50 bg-background/50 text-foreground resize-none focus:outline-none"
          />
          <p className="text-muted-foreground text-sm">Texto reconhecido em tempo real</p>
        </div>

        {/* Botão principal */}
        <div className="flex flex-col items-center justify-center space-y-8">
          <button
            onClick={() => {
              const recognition = recognitionRef.current;
              if (recognition) {
                if (isListening) {
                  recognition.stop();
                  setStatusMessage("🛑 Escuta parada manualmente.");
                } else {
                  recognition.start();
                  setStatusMessage("🎧 Escutando novamente...");
                }
                setIsListening(!isListening);
              }
            }}
            className={`relative w-32 h-32 rounded-full transition-all duration-300 transform active:scale-95 ${
              buttonState === "recording"
                ? "bg-gradient-hover shadow-glow animate-pulse"
                : "bg-gradient-accent hover:bg-gradient-hover shadow-card hover:shadow-hover hover:scale-105"
            }`}
          >
            <div className="flex items-center justify-center w-full h-full">
              {buttonState === "recording" ? (
                <Square size={48} className="text-primary-foreground" fill="currentColor" />
              ) : (
                <Mic size={48} className="text-primary-foreground" />
              )}
            </div>
          </button>

          <p className="text-sm text-muted-foreground">
            {isListening ? "Escutando automaticamente..." : "Clique para iniciar manualmente"}
          </p>
        </div>
      </div>
    </div>
  );
};

export default Voice_STT_Test;
