import { ArrowLeft, Mic, Square } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState, useRef } from "react";

const Voice = () => {
  const navigate = useNavigate();
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await sendAudioToEndpoint(audioBlob);
        
        // Stop all tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Erro ao acessar o microfone. Verifique as permissões.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsLoading(true);
    }
  };

  const sendAudioToEndpoint = async (audioBlob: Blob) => {
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch('/api/record', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Failed to send audio');
      }

      console.log('Audio sent successfully');
    } catch (error) {
      console.error('Error sending audio:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleButtonClick = () => {
    if (isRecording) {
      stopRecording();
    } else if (!isLoading) {
      startRecording();
    }
  };

  const getButtonState = () => {
    if (isLoading) return 'loading';
    if (isRecording) return 'recording';
    return 'idle';
  };

  const buttonState = getButtonState();

  return (
    <div className="min-h-screen bg-gradient-primary">
      <div className="container mx-auto px-4 py-12">
        {/* Back button */}
        <button
          onClick={() => navigate("/")}
          className="inline-flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors duration-200 mb-8"
        >
          <ArrowLeft size={20} />
          <span>Back to Home</span>
        </button>

        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Voice Control
          </h1>
          <p className="text-lg text-muted-foreground max-w-md mx-auto">
            Click the microphone to record your voice command
          </p>
        </div>

        {/* Voice Recording Button */}
        <div className="flex flex-col items-center justify-center space-y-8">
          <button
            onClick={handleButtonClick}
            disabled={isLoading}
            className={`relative w-32 h-32 rounded-full transition-all duration-300 transform active:scale-95 ${
              buttonState === 'recording'
                ? 'bg-gradient-hover shadow-glow animate-pulse'
                : buttonState === 'loading'
                ? 'bg-muted cursor-not-allowed'
                : 'bg-gradient-accent hover:bg-gradient-hover shadow-card hover:shadow-hover hover:scale-105'
            }`}
          >
            <div className="flex items-center justify-center w-full h-full">
              {buttonState === 'recording' ? (
                <Square size={48} className="text-primary-foreground" fill="currentColor" />
              ) : buttonState === 'loading' ? (
                <div className="w-12 h-12 border-4 border-muted-foreground border-t-transparent rounded-full animate-spin" />
              ) : (
                <Mic size={48} className="text-primary-foreground" />
              )}
            </div>
            
            {/* Recording indicator ring */}
            {buttonState === 'recording' && (
              <div className="absolute inset-0 rounded-full border-4 border-tech-blue animate-ping opacity-30" />
            )}
          </button>

          {/* Status Text */}
          <div className="text-center">
            <p className="text-xl font-medium text-foreground mb-2">
              {buttonState === 'idle' && 'Tap to start recording'}
              {buttonState === 'recording' && 'Recording... Tap to stop'}
              {buttonState === 'loading' && 'Processing audio...'}
            </p>
            
            {buttonState === 'recording' && (
              <div className="flex items-center justify-center space-x-2 text-tech-blue">
                <div className="w-2 h-2 bg-tech-blue rounded-full animate-pulse" />
                <span className="text-sm">Listening</span>
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="max-w-md mx-auto mt-16">
          <div className="bg-gradient-card rounded-2xl p-6 shadow-card border border-border/50">
            <h3 className="font-semibold text-foreground mb-3">Instructions:</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-tech-blue rounded-full" />
                <span>Click to start recording</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-tech-blue rounded-full" />
                <span>Speak your command clearly</span>
              </li>
              <li className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-tech-blue rounded-full" />
                <span>Click again to stop and send</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Voice;