import asyncio
import json
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager



# 👉 Import ajustado (usa src.)
from tratamento_response_IA import processar_resposta, inicializar_dispositivos, DISPOSITIVOS


N8N_LOGIN_URL = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/login_user_webhook"
N8N_AUTH_CHECK_URL = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/auth_check_user"


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
    "http://localhost:8080/notificar-mensagem-ia",
    "http://localhost:8000/login_user"
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

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login_user")
async def login_user(request: Request, response: Response, data: LoginRequest):
    """
    Endpoint seguro de login.
    Chama o webhook n8n de login e grava o session_id como cookie HttpOnly.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            n8n_response = await client.post(
                N8N_LOGIN_URL,
                json={"email": data.email, "password": data.password}
            )

        if n8n_response.status_code != 200:
            raise HTTPException(status_code=401, detail=f"Erro N8N: {n8n_response.status_code}")

        result = n8n_response.json()
        print("[N8N LOGIN RESULT]", result)

        session_id = result.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="Login sem session_id retornado")

        # Define cookie HttpOnly (TTL já gerenciado pelo n8n/Redis)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  # alterar para True em produção
            samesite="lax",
            max_age=3600
        )

        return {"status": "success", "user": result.get("user")}

    except Exception as e:
        print(f"[ERRO LOGIN_USER] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth_check_user")
async def auth_check_user(request: Request):
    """
    Valida o cookie de sessão com o webhook n8n.
    """
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="Cookie de sessão ausente")

        async with httpx.AsyncClient(timeout=10.0) as client:
            n8n_response = await client.get(f"{N8N_AUTH_CHECK_URL}?session_id={session_id}")

        if n8n_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

        data = n8n_response.json()
        return {"status": "valid", "data": data}

    except Exception as e:
        print(f"[ERRO AUTH_CHECK] {e}")
        raise HTTPException(status_code=500, detail=str(e))



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
