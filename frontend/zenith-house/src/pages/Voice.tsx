// src/pages/Voice.tsx
import { useEffect, useState, useRef } from "react";
import { ArrowLeft, Mic, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Voice = () => {
  const navigate = useNavigate();

  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState("");
  const [hotwordMessage, setHotwordMessage] = useState("");
  const [inputText, setInputText] = useState(""); // 🆕 texto digitado (simulação de fala)
  const socketRef = useRef<WebSocket | null>(null);
  const hotwordRef = useRef<WebSocket | null>(null);

  const WS_BASE_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8008";

  // =====================================================
  // 🧠 HOTWORD - conecta automaticamente ao abrir a tela
  // =====================================================
  const connectHotwordWebSocket = () => {
    try {
      const ws = new WebSocket(`${WS_BASE_URL}/ws-hotword`);

      ws.onopen = () => {
        console.log("👂 [HOTWORD] Conectado.");
        setHotwordMessage("✅ Detector de hotword ativo (diga ou digite 'bob').");
      };

      ws.onmessage = (event) => {
        console.log("📩 [HOTWORD]", event.data);
        setHotwordMessage(event.data);

        // Quando o servidor detectar a hotword, ativa o modo voz
        // ✅ Agora só ativa se a mensagem realmente indicar detecção
        if (
          event.data.toLowerCase().includes("hotword detectada") ||
          event.data.toLowerCase().startsWith("🚀")
        ) {
          console.log("🎯 Hotword confirmada pelo servidor, ativando modo comando...");
          ws.close();
          connectVoiceWebSocket();
        }

      };

      ws.onerror = (error) => {
        console.error("⚠️ [HOTWORD] Erro:", error);
        setHotwordMessage("❌ Erro no detector de hotword.");
      };

      ws.onclose = () => {
        console.log("🔌 [HOTWORD] Conexão encerrada.");
      };

      hotwordRef.current = ws;
    } catch (error) {
      console.error("Erro ao conectar hotword:", error);
      setHotwordMessage("❌ Falha ao conectar hotword.");
    }
  };

  // =====================================================
  // 🎙️ VOICE - ativa após hotword ser detectada
  // =====================================================
  const connectVoiceWebSocket = async (): Promise<void> => {
    try {
      setIsLoading(true);
      const ws = new WebSocket(`${WS_BASE_URL}/ws-voice`);

      ws.onopen = () => {
        console.log("🎧 [VOICE] Conectado.");
        setConnectionMessage("✅ Modo comando ativo!");
        setIsRecording(true);
        setIsLoading(false);
      };

      ws.onmessage = (event) => {
        console.log("📩 [VOICE]", event.data);
        setConnectionMessage(event.data);

        // Quando o servidor indicar que o comando foi processado
        if (event.data.toLowerCase().includes("comando processado")) {
          ws.close(); // encerra o modo voz
          setTimeout(connectHotwordWebSocket, 1000); // reativa o hotword após 1s
        }
      };

      ws.onerror = (error) => {
        console.error("⚠️ [VOICE] Erro:", error);
        setConnectionMessage("❌ Erro ao conectar ao servidor de voz.");
        setIsLoading(false);
      };

      ws.onclose = () => {
        console.log("🔌 [VOICE] Conexão encerrada.");
        setIsRecording(false);
        setConnectionMessage("🔌 Servidor de voz desconectado.");
      };

      socketRef.current = ws;
    } catch (error) {
      console.error("Erro ao conectar ao WebSocket:", error);
      setConnectionMessage("❌ Falha ao conectar ao servidor de voz.");
      setIsLoading(false);
    }
  };

  // =====================================================
  // 🔄 Controle de ciclo de vida da tela
  // =====================================================
  useEffect(() => {
    connectHotwordWebSocket();

    return () => {
      // Fecha conexões ao sair
      if (hotwordRef.current?.readyState === WebSocket.OPEN) hotwordRef.current.close();
      if (socketRef.current?.readyState === WebSocket.OPEN) socketRef.current.close();
    };
  }, []);

  // =====================================================
  // 🎤 Simulação de fala - decide o que ativar
  // =====================================================
  const handleSimulateVoice = () => {
    const text = inputText.trim().toLowerCase();
    if (!text) return;

    // Caso 1: Hotword detectada
    if (text.includes("bob")) {
      if (hotwordRef.current?.readyState === WebSocket.OPEN) {
        hotwordRef.current.send("bob");
        setHotwordMessage("🚀 Hotword detectada!");
      }
    }
    // Caso 2: Comando
    else if (isRecording && socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(text);
      setConnectionMessage(`🎤 Comando enviado: "${text}"`);
    }
    // Caso 3: Nada conectado
    else {
      setConnectionMessage("⚠️ Nenhum modo ativo no momento.");
    }

    setInputText("");
  };

  // =====================================================
  // 🎙️ Botão principal (design original)
  // =====================================================
  const buttonState = isLoading ? "loading" : isRecording ? "recording" : "idle";

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
          <h1 className="text-4xl font-bold text-foreground mb-4">Voice Control</h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            Type your voice command below to simulate what you would say aloud.
          </p>
        </div>

        {/* Status do hotword */}
        <div className="text-center mb-6">
          <p className="text-sm text-tech-blue">{hotwordMessage}</p>
        </div>

        {/* Caixa de simulação de fala */}
        <div className="flex flex-col items-center space-y-4 mb-10">
          <input
            type="text"
            placeholder="Ex: bob, ligar a luz..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSimulateVoice()}
            className="px-4 py-2 rounded-lg w-80 border border-border/50 bg-background/50 text-foreground focus:outline-none focus:ring-2 focus:ring-tech-blue transition"
          />
          <button
            onClick={handleSimulateVoice}
            className="px-6 py-2 rounded-md bg-gradient-accent hover:bg-gradient-hover shadow-md text-primary-foreground transition"
          >
            Simular Fala
          </button>
        </div>

        {/* Botão principal */}
        <div className="flex flex-col items-center justify-center space-y-8">
          <button
            disabled={isLoading}
            className={`relative w-32 h-32 rounded-full transition-all duration-300 transform active:scale-95 ${
              buttonState === "recording"
                ? "bg-gradient-hover shadow-glow animate-pulse"
                : buttonState === "loading"
                ? "bg-muted cursor-not-allowed"
                : "bg-gradient-accent hover:bg-gradient-hover shadow-card hover:shadow-hover hover:scale-105"
            }`}
          >
            <div className="flex items-center justify-center w-full h-full">
              {buttonState === "recording" ? (
                <Square size={48} className="text-primary-foreground" fill="currentColor" />
              ) : buttonState === "loading" ? (
                <div className="w-12 h-12 border-4 border-muted-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                <Mic size={48} className="text-primary-foreground" />
              )}
            </div>

            {buttonState === "recording" && (
              <div className="absolute inset-0 rounded-full border-4 border-tech-blue animate-ping opacity-30" />
            )}
          </button>

          {/* Status */}
          <div className="text-center">
            <p className="text-xl font-medium text-foreground mb-2">
              {buttonState === "idle" && "Waiting for hotword..."}
              {buttonState === "recording" && "Listening for command..."}
              {buttonState === "loading" && "Connecting..."}
            </p>

            {connectionMessage && (
              <p className="text-sm text-muted-foreground mt-1">{connectionMessage}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Voice;
