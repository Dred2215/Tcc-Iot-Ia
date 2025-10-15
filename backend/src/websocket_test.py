# websocket_test.py
import asyncio
import json
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import service_account
from google.cloud import speech as gspeech  # <- alias para evitar colisões
import uvicorn

app = FastAPI()

# =======================
# CORS
# =======================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =======================
# Credenciais e paths
# =======================
BASE_DIR = Path(__file__).resolve().parent.parent  # volta da pasta 'src'
SERVICE_ACCOUNT_PATH = BASE_DIR / "secret" / "automa-code-348d4b5cc3bd.json"

credentials = service_account.Credentials.from_service_account_file(str(SERVICE_ACCOUNT_PATH))
speech_client = gspeech.SpeechClient(credentials=credentials)

# Mantido só para o /ws echo (não-STT)
streaming_config_default = gspeech.StreamingRecognitionConfig(
    config=gspeech.RecognitionConfig(
        encoding=gspeech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="pt-BR",
    ),
    interim_results=True,
)

# =======================
# /ws - endpoint simples (echo / teste)
# =======================
@app.websocket("/ws")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    print("🔌 [/ws] Cliente conectado!")
    try:
        while True:
            data = await websocket.receive()
            if "text" in data:
                msg = data["text"]
                if msg == "END_OF_STREAM":
                    await websocket.send_text("OK: fim de stream recebido.")
                    print("🛑 [/ws] Fim do stream recebido.")
                    break
                await websocket.send_text(f"echo: {msg}")
            elif "bytes" in data and data["bytes"] is not None:
                b = data["bytes"]
                await websocket.send_text(json.dumps({"type": "bytes", "len": len(b)}))
    except Exception as e:
        print("⚠️ [/ws] Cliente desconectado:", e)
    finally:
        await websocket.close()
        print("🔌 [/ws] Conexão encerrada.")


# =====================================================================
# /ws-stt - streaming real-time com ffmpeg → PCM → Google STT (streaming)
# =====================================================================
@app.websocket("/ws-stt")
async def websocket_stt(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Cliente conectado (STT)")

    # Importações locais apenas do que NÃO conflita com google.cloud.speech
    from queue import Queue
    from threading import Thread
    from speech_api import load_credentials  # **somente credenciais**, nada de helpers de STT

    async def _read_ffmpeg_stdout_to_queue(
        proc: asyncio.subprocess.Process,
        target_q: Queue,
        *,
        chunk_size: int = 3200
    ):
        try:
            while True:
                chunk = await proc.stdout.read(chunk_size)
                if not chunk:
                    break
                target_q.put(chunk)
        finally:
            target_q.put(None)

    async def _drain_ffmpeg_stderr(proc: asyncio.subprocess.Process):
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                print("[ffmpeg]", line.decode(errors="ignore").strip())
        except Exception:
            pass

    def _stt_worker(pcm_q: Queue, result_q: Queue, language_code: str = "pt-BR"):
        try:
            creds = load_credentials()
            client = gspeech.SpeechClient(credentials=creds)

            config = gspeech.RecognitionConfig(
                encoding=gspeech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                model="default",
            )
            streaming_config = gspeech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
                single_utterance=False,
            )

            def requests_generator():
                yield gspeech.StreamingRecognizeRequest(streaming_config=streaming_config)
                while True:
                    chunk = pcm_q.get()
                    if chunk is None:
                        break
                    if not chunk:
                        continue
                    yield gspeech.StreamingRecognizeRequest(audio_content=chunk)

            # ✅ Chamada direta do RPC (sem helper, sem keyword)
            rpc = client.transport.streaming_recognize
            responses = rpc(requests_generator())

            for response in responses:
                for result in response.results:
                    if not result.alternatives:
                        continue
                    alt = result.alternatives[0]
                    if result.is_final:
                        result_q.put({"type": "final", "text": alt.transcript, "final": True})
                    else:
                        result_q.put({"type": "partial", "text": alt.transcript, "final": False})

        except Exception as e:
            result_q.put({"type": "error", "message": str(e)})
        finally:
            result_q.put({"type": "done"})



    # ffmpeg baixa latência: webm/opus → PCM 16k mono s16le
    ffmpeg_cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-probesize", "32",
        "-analyzeduration", "0",
        "-use_wallclock_as_timestamps", "1",
        "-i", "pipe:0",
        "-ac", "1",
        "-ar", "16000",
        "-f", "s16le",
        "pipe:1",
    ]

    proc: Optional[asyncio.subprocess.Process] = None
    from queue import Queue as _Q
    pcm_queue: _Q = _Q(maxsize=100)
    result_queue: _Q = _Q()

    try:
        # Inicia o ffmpeg
        proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        pump_task = asyncio.create_task(_read_ffmpeg_stdout_to_queue(proc, pcm_queue))
        stderr_task = asyncio.create_task(_drain_ffmpeg_stderr(proc))

        # Worker STT (thread) consumindo PCM e publicando resultados
        stt_thread = Thread(target=_stt_worker, args=(pcm_queue, result_queue), daemon=True)
        stt_thread.start()

        async def forward_results():
            loop = asyncio.get_event_loop()
            while True:
                item = await loop.run_in_executor(None, result_queue.get)
                if not item:
                    continue
                if item.get("type") == "done":
                    break
                await websocket.send_text(json.dumps(item, ensure_ascii=False))

        forward_task = asyncio.create_task(forward_results())

        # Loop principal: recebe bytes do navegador e alimenta o ffmpeg
        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"]:
                text = msg["text"]
                if text == "END_OF_STREAM":
                    print("[WS] Fim do stream recebido (STT)")
                    if proc and proc.stdin:
                        try:
                            proc.stdin.write_eof()
                        except Exception:
                            pass
                    break
                else:
                    await websocket.send_text(json.dumps({"type": "info", "text": text}))
            elif "bytes" in msg and msg["bytes"] is not None:
                data = msg["bytes"]
                if proc and proc.stdin:
                    proc.stdin.write(data)
                    await proc.stdin.drain()
                if len(data) > 0:
                    print(f"[WS] Recebido {len(data)} bytes do cliente")

        if proc:
            try:
                await proc.wait()
            except Exception:
                pass

        await asyncio.gather(pump_task, stderr_task, return_exceptions=True)
        await forward_task

    except Exception as e:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
        print("[WS] Erro (STT):", e)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
        print("[WS] Conexão encerrada (STT)")


# =======================
# Run
# =======================
if __name__ == "__main__":
    # Ex.: uvicorn websocket_test:app --host 0.0.0.0 --port 8005 --reload
    uvicorn.run(app, host="0.0.0.0", port=8005)
