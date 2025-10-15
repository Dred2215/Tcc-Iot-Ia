import { useEffect, useState, useRef } from "react";
import { ArrowLeft, Mic, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";

const WebVoice_test = () => {
  const navigate = useNavigate();

  // Estados visuais
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [transcript, setTranscript] = useState<string>("");
  const [finalText, setFinalText] = useState<string>("");
  const [interimText, setInterimText] = useState<string>("");
  const [finalOnlyText, setFinalOnlyText] = useState<string>("");

  // Referências
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // ----------------------------
  // 1️⃣ Conecta WebSocket (modo comando)
  // ----------------------------
  const connectWebSocket = (): Promise<WebSocket> => {
    return new Promise((resolve, reject) => {
      try {
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const host = window.location.hostname;
        const ws = new WebSocket(`${protocol}://${host}:8005/ws-stt`);

        ws.onopen = () => {
          console.log("✅ [Main] WebSocket conectado.");
          setIsConnected(true);
          resolve(ws);
        };

        ws.onerror = (err) => {
          console.error("⚠️ [Main] Erro no WebSocket:", err);
          reject(err);
        };

        ws.onclose = () => {
          console.warn("🔌 [Main] WebSocket desconectado.");
          setIsConnected(false);
        };

        ws.onmessage = async (event) => {
          try {
            const msg = JSON.parse(event.data);

            if (msg.type === "partial" || msg.type === "final") {
              const text = msg.text?.trim() || "";
              console.log(`💬 [Main] (${msg.type}) → ${text}`);

              if (msg.type === "partial") {
                setInterimText(text);
              }

              if (msg.type === "final") {
                setFinalText((prev) => prev + " " + text);
                setInterimText("");

                // Quando o texto final completo chega
                if (msg.final === true) {
                  setFinalOnlyText(text || "");

                  // ⚙️ Filtro de modo de gravação
                  if (isRecording) {
                    console.log("🕓 [Main] Ignorando mensagem (modo passivo):", text);
                  } else {
                    try {
                      // 🔸 Envia o texto final para o backend
                      const response = await fetch("http://localhost:8000/voice_command", {
                        method: "POST",
                        headers: {
                          "Content-Type": "application/json",
                        },
                        body: JSON.stringify({ message: text }),
                      });

                      if (!response.ok) {
                        throw new Error(`Erro HTTP: ${response.status}`);
                      }

                      const data = await response.json();
                      console.log("🤖 Resposta do sistema:", data);

                    } catch (err) {
                      console.error("❌ Erro ao enviar comando de voz:", err);
                    }
                  }

                  try {
                    stopRecording(false); // Para a gravação
                    // Volta ao modo "wake listener" após 1s
                    setTimeout(() => startWakeListener(), 1000);
                  } catch (err) {
                    console.error("Erro ao parar gravação:", err);
                  }
                }
              }
            }
          } catch {
            console.log("📨 [Main] Mensagem não-JSON:", event.data);
          }
        };
      } catch (err) {
        reject(err);
      }
    });
  };

  // ----------------------------
  // 2️⃣ Inicia gravação ativa (modo comando)
  // ----------------------------
  const startRecording = async () => {
    try {
      console.log("🎬 [Main] Iniciando gravação de comando...");
      setIsLoading(true);
      const ws = await connectWebSocket();
      socketRef.current = ws;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType =
        MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
          ? "audio/webm;codecs=opus"
          : "audio/webm";

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond: 128000,
      });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          const buf = await event.data.arrayBuffer();
          ws.send(buf);
          console.log(`🎧 [Main] Enviado chunk (${event.data.size} bytes)`);
        }
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        console.log("🛑 [Main] Gravação encerrada, enviando END_OF_STREAM.");
        if (ws.readyState === WebSocket.OPEN) ws.send("END_OF_STREAM");
      };

      mediaRecorder.start(250);
      console.log("🎙️ [Main] Gravando áudio do comando...");
      setIsRecording(true);
      setIsLoading(false);
    } catch (error) {
      console.error("❌ [Main] Erro ao iniciar gravação:", error);
      setIsLoading(false);
    }
  };

  // ----------------------------
  // 3️⃣ Escuta passiva ("bob")
  // ----------------------------
  const startWakeListener = async () => {
    try {
      console.log("🎧 [Wake] Iniciando escuta passiva...");
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      const host = window.location.hostname;
      const ws = new WebSocket(`${protocol}://${host}:8005/ws-stt`);
      socketRef.current = ws;

      ws.onopen = async () => {
        console.log("✅ [Wake] WebSocket conectado (modo passivo).");
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType =
          MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
            ? "audio/webm;codecs=opus"
            : "audio/webm";

        const mediaRecorder = new MediaRecorder(stream, {
          mimeType,
          audioBitsPerSecond: 128000,
        });
        mediaRecorderRef.current = mediaRecorder;

        mediaRecorder.ondataavailable = async (event) => {
          if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
            const buf = await event.data.arrayBuffer();
            ws.send(buf);
            console.log(`🎧 [Wake] Enviado chunk (${event.data.size} bytes)`);
          }
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if ((msg.type === "partial" || msg.type === "final") && msg.text) {
              const text = msg.text.toLowerCase().trim();
              console.log(`🗣️ [Wake] (${msg.type}) → "${text}"`);
              setTranscript((prev) => prev + "\n" + text);

              if (msg.type === "final" && msg.final === true) {
                setFinalOnlyText(msg.text || "");
              }

              if (text.includes("bob")) {
                console.log("🚀 [Wake] Palavra 'bob' detectada!");
                try {
                  mediaRecorder.stop();
                  stream.getTracks().forEach((t) => t.stop());
                } catch {}
                // ❌ NÃO fecha o socket — mantém aberto
                // ✅ inicia modo comando
                setTimeout(() => startRecording(), 500);
              }
            }
          } catch (err) {
            console.error("⚠️ [Wake] Erro ao processar mensagem:", err);
          }
        };

        mediaRecorder.start(250);
        console.log("🎙️ [Wake] Microfone ativo — diga 'bob' para ativar.");
      };

      ws.onerror = (err) => console.error("⚠️ [Wake] Erro no WebSocket:", err);
      ws.onclose = () => console.log("🔌 [Wake] Listener encerrado.");
    } catch (err) {
      console.error("❌ [Wake] Erro ao iniciar listener:", err);
    }
  };

  // ----------------------------
  // 4️⃣ Parar gravação (sem fechar WebSocket)
  // ----------------------------
  const stopRecording = (closeSocket: boolean = false) => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      console.log("🛑 [Main] Encerrando gravação...");
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
    if (closeSocket && socketRef.current?.readyState === WebSocket.OPEN) {
      console.log("🔌 Encerrando WebSocket conforme solicitado.");
      socketRef.current.close();
      setIsConnected(false);
    }
  };

  // 🧩 Inicia automaticamente o listener ao abrir a tela
  useEffect(() => {
    startWakeListener();
    return () => {
      stopRecording(true); // encerra gravação e socket ao sair da página
    };
  }, []);

  // ----------------------------
  // 5️⃣ Interface
  // ----------------------------
  const buttonState = isLoading
    ? "loading"
    : isRecording
    ? "recording"
    : "idle";

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        <button
          onClick={() => navigate("/")}
          className="inline-flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8"
        >
          <ArrowLeft size={20} />
          <span>Back to Home</span>
        </button>

        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            WebSocket Voice Control
          </h1>
          <p className="text-muted-foreground">
            Say "bob" to activate the command mode
          </p>
        </div>

        <div className="flex flex-col items-center justify-center space-y-8">
          <button
            onClick={() =>
              isRecording ? stopRecording() : startRecording()
            }
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
                <Square
                  size={48}
                  className="text-primary-foreground"
                  fill="currentColor"
                />
              ) : buttonState === "loading" ? (
                <div className="w-12 h-12 border-4 border-muted-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                <Mic size={48} className="text-primary-foreground" />
              )}
            </div>
          </button>

          <p className="text-center text-foreground text-lg">
            {buttonState === "idle" && "Tap to start recording"}
            {buttonState === "recording" && "Recording... Tap to stop"}
            {buttonState === "loading" && "Connecting..."}
          </p>

          <div className={`text-sm ${isConnected ? "text-green-500" : "text-red-500"}`}>
            {isConnected ? "Connected to WebSocket" : "Not connected"}
          </div>
        </div>

        <div className="mt-10 max-w-2xl mx-auto bg-gradient-card rounded-xl p-6 text-foreground border border-border/50 shadow-card">
          <h3 className="font-semibold mb-2">Transcription:</h3>
          <pre className="whitespace-pre-wrap text-sm text-muted-foreground">
            {finalOnlyText || "Listening..."}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default WebVoice_test;
