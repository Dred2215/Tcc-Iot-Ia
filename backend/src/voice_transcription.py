"""
Transcricao de audio sob demanda usando a lib SpeechRecognition
(API publica/gratuita do Google, sem credenciais).

Substitui o fluxo antigo baseado em Web Speech API do navegador +
multiplos WebSockets (ws-ping, ws-hotword, ws-voice).
"""

import subprocess
import tempfile
from pathlib import Path

import speech_recognition as sr


class TranscriptionError(Exception):
    pass


def _convert_to_wav(input_path: Path, output_path: Path) -> None:
    """Converte o audio recebido (webm/ogg/etc) para WAV usando ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(input_path), str(output_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as e:
        raise TranscriptionError("ffmpeg não encontrado no servidor.") from e
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        raise TranscriptionError(f"Falha ao converter áudio: {stderr}") from e


def transcrever_audio_bytes(audio_bytes: bytes, filename_hint: str = "audio.webm") -> str:
    """
    Recebe os bytes de um arquivo de áudio (ex: gravado via MediaRecorder
    no navegador), converte para WAV e transcreve usando o Google Speech
    Recognition público (idioma pt-BR). Retorna o texto transcrito.
    """
    suffix = Path(filename_hint).suffix or ".webm"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        input_path = tmp_dir_path / f"input{suffix}"
        wav_path = tmp_dir_path / "converted.wav"

        input_path.write_bytes(audio_bytes)
        _convert_to_wav(input_path, wav_path)

        recognizer = sr.Recognizer()
        with sr.AudioFile(str(wav_path)) as source:
            audio = recognizer.record(source)

        try:
            texto = recognizer.recognize_google(audio, language="pt-BR")
        except sr.UnknownValueError as e:
            raise TranscriptionError("Não foi possível entender o áudio.") from e
        except sr.RequestError as e:
            raise TranscriptionError(f"Erro ao consultar o serviço de transcrição: {e}") from e

        return texto
