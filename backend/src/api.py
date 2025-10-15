import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# 👉 Import ajustado (usa src.)
from tratamento_response_IA import processar_resposta, inicializar_dispositivos, DISPOSITIVOS

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Servidor iniciando...")
    print(f"✅ VARIÁVEL DE AMBIENTE PORT: {os.getenv('PORT')}")

    # 🚀 Inicializa os dispositivos/cenas aqui
    try:
        inicializar_dispositivos()
        print("[INIT] Dispositivos e cenas prontos:", list(DISPOSITIVOS.keys()))
    except Exception as e:
        print(f"[ERRO] Falha ao inicializar dispositivos/cenas: {e}")

    print("✅ Backend pronto para receber conexões!")
    yield
    print("🛑 Encerrando aplicação...")

app = FastAPI(lifespan=lifespan)

# 🔒 CORS fixo: apenas o frontend homolog pode acessar
origins = [
    "https://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
    "http://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
    "http://localhost:8000/record",
    "http://localhost:8080",
    "http://localhost:8080/text",
    "http://localhost:8080/notificar-mensagem-ia"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Modelo da request
class MensagemRequest(BaseModel):
    mensagem: Optional[str] = ""
    comando: Optional[Any] = ""
    tipo: Optional[str] = ""

# ✅ Endpoint de notificação
@app.post("/notificar-mensagem-ia")
async def notificar_mensagem_ia(req: MensagemRequest):
    print(f"[LOG] Corpo recebido: mensagem='{req.mensagem}', comando='{req.comando}', tipo='{req.tipo}'")

    # Estrutura interna
    class IA:
        message = {
            "message": req.mensagem,
            "command": req.comando
        }

    comando_obj = IA.message["command"]

    # Se for string JSON, tenta decodificar
    if isinstance(comando_obj, str) and comando_obj.strip().startswith(('[', '{')):
        try:
            comando_obj = json.loads(comando_obj)
        except json.JSONDecodeError:
            print(f"[ERRO] Falha ao decodificar o JSON do comando: {comando_obj}")
            raise HTTPException(status_code=400, detail="Comando em formato JSON inválido.")

    # Se for comando IoT → dispara processamento
    if req.tipo == "IOT" and comando_obj:
        print(f"[AÇÃO] Executando comando IOT: {comando_obj}")
        asyncio.create_task(processar_resposta(comando_obj))
        return {"status": "Comando IOT recebido e sendo processado em segundo plano."}

    return {"status": "Notificação recebida", "data": IA.message}


# ✅ Endpoint para comandos de voz (texto final do WebSocket)
class VoiceCommand(BaseModel):
    message: str

@app.post("/voice_command")
async def voice_command(req: VoiceCommand):
    """
    Recebe o texto final reconhecido pela voz e envia para o sistema de tratamento.
    """
    try:
        print(f"[🎙️ VOICE] Comando recebido: {req.message}")

        # 🔹 Envia o texto para o mesmo fluxo usado no chat textual
        resposta = await processar_resposta(req.message)

        print(f"[🎯 VOICE] Resposta gerada: {resposta}")
        return {"status": "ok", "response": resposta}

    except Exception as e:
        print(f"[ERRO VOICE] {e}")
        raise HTTPException(status_code=500, detail=str(e))




# ✅ Endpoint de teste
@app.get("/ping")
async def ping():
    return {"message": "Backend está online 🚀"}

@app.post("/record")
async def record(audio: UploadFile = File(...)):
    if not audio.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo de audio enviado.")

    content_type = (audio.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Tipo de arquivo invalido. Envie um audio.")

    base_path = Path(__file__).resolve().parent.parent
    audio_dir = base_path / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    original_suffix = Path(audio.filename).suffix
    extension = original_suffix if original_suffix else ".webm"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    unique_id = uuid4().hex
    filename = f"recording_{timestamp}_{unique_id}{extension}"
    file_path = audio_dir / filename

    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo de audio vazio.")

    with file_path.open("wb") as buffer:
        buffer.write(data)

    print(f"[AUDIO] Arquivo salvo em {file_path}")

    return {
        "status": "ok",
        "filename": filename,
        "relative_path": f"audio/{filename}",
    }




# Middleware de log
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
