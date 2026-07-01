import { useRef, useState } from "react";
import { ArrowLeft, Loader2, Mic, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { transcribeAudio } from "@/services/voice_transcription";
import { sendUserMessage } from "@/services/user_message_input_chat";

type VoiceState = "idle" | "recording" | "transcribing" | "processing";

const Voice_STT_Test = () => {
  const navigate = useNavigate();

  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [statusMessage, setStatusMessage] = useState("Clique no microfone para gravar um comando.");
  const [recognizedText, setRecognizedText] = useState("");
  const [aiResponse, setAiResponse] = useState("");
  const [error, setError] = useState("");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const stopStream = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  const startRecording = async () => {
    setError("");
    setRecognizedText("");
    setAiResponse("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        stopStream();
        const audioBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        void handleRecordingFinished(audioBlob);
      };

      mediaRecorder.start();
      setVoiceState("recording");
      setStatusMessage("Gravando... clique novamente para parar.");
    } catch (err) {
      console.error("Erro ao acessar o microfone:", err);
      setError("Não foi possível acessar o microfone. Verifique as permissões do navegador.");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
  };

  const handleRecordingFinished = async (audioBlob: Blob) => {
    setVoiceState("transcribing");
    setStatusMessage("Transcrevendo áudio...");

    try {
      const texto = await transcribeAudio(audioBlob);
      setRecognizedText(texto);

      setVoiceState("processing");
      setStatusMessage("Processando comando...");

      const response = await sendUserMessage(texto);
      setAiResponse(response.respostaIA || "Comando processado.");
      setStatusMessage("Clique no microfone para gravar um novo comando.");
    } catch (err) {
      console.error("Erro no fluxo de voz:", err);
      setError(err instanceof Error ? err.message : "Falha ao processar o áudio. Tente novamente.");
      setStatusMessage("Clique no microfone para gravar um comando.");
    } finally {
      setVoiceState("idle");
    }
  };

  const handleMicClick = () => {
    if (voiceState === "recording") {
      stopRecording();
      return;
    }
    if (voiceState === "idle") {
      void startRecording();
    }
  };

  const isBusy = voiceState === "transcribing" || voiceState === "processing";

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

        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-foreground mb-4">Voice Control</h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            Clique no microfone, fale o comando e clique novamente para enviar.
          </p>
        </div>

        <div className="text-center mb-6">
          <p className="text-sm text-tech-blue">{statusMessage}</p>
          {error && <p className="text-sm text-destructive mt-2">{error}</p>}
        </div>

        <div className="flex flex-col items-center space-y-4 mb-10">
          <textarea
            readOnly
            value={recognizedText}
            placeholder="O texto transcrito aparecerá aqui..."
            className="w-96 h-40 p-4 rounded-lg border border-border/50 bg-background/50 text-foreground resize-none focus:outline-none"
          />
          <p className="text-muted-foreground text-sm">Texto transcrito do último comando</p>
        </div>

        <div className="flex flex-col items-center justify-center space-y-8">
          <button
            onClick={handleMicClick}
            disabled={isBusy}
            className={`relative w-32 h-32 rounded-full transition-all duration-300 transform active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed ${
              voiceState === "recording"
                ? "bg-gradient-hover shadow-glow animate-pulse"
                : "bg-gradient-accent hover:bg-gradient-hover shadow-card hover:shadow-hover hover:scale-105"
            }`}
          >
            <div className="flex items-center justify-center w-full h-full">
              {isBusy ? (
                <Loader2 size={48} className="text-primary-foreground animate-spin" />
              ) : voiceState === "recording" ? (
                <Square size={48} className="text-primary-foreground" fill="currentColor" />
              ) : (
                <Mic size={48} className="text-primary-foreground" />
              )}
            </div>
          </button>

          <p className="text-sm text-muted-foreground">
            {voiceState === "recording"
              ? "Gravando... clique para parar e enviar"
              : isBusy
                ? "Aguarde..."
                : "Clique para gravar um comando"}
          </p>

          {/* Resposta do assistente (confirmação de ação ou resposta da IA) */}
          {(aiResponse || isBusy) && (
            <div className="w-full max-w-md bg-gradient-card rounded-2xl p-6 shadow-card border border-border/50 text-center">
              <h3 className="text-sm font-semibold text-tech-blue uppercase tracking-wide mb-2">
                Resposta do assistente
              </h3>
              <p className="text-sm text-foreground/90 leading-relaxed">
                {isBusy ? "Aguardando resposta..." : aiResponse}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Voice_STT_Test;
