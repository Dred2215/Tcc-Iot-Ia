import asyncio
import json
import os
import httpx
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from urllib.parse import urlsplit



# 👉 Import ajustado (usa src.)
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from tratamento_response_IA import processar_resposta, inicializar_dispositivos, DISPOSITIVOS


N8N_LOGIN_URL = os.getenv("N8N_LOGIN_URL")
N8N_AUTH_CHECK_URL = os.getenv("N8N_AUTH_CHECK_URL")
N8N_LOG_WEBHOOK = os.getenv("N8N_LOG_WEBHOOK")

FRONTEND_URL = os.getenv("FRONTEND_URL")
FRONTEND_HOMOLOG_URL = os.getenv(
    "FRONTEND_HOMOLOG_URL",
    "https://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
)
FRONTEND_HOMOLOG_HTTP_URL = os.getenv(
    "FRONTEND_HOMOLOG_HTTP_URL",
    "http://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
)
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL") or os.getenv("BACKEND_URL")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE")


def _parse_bool_env(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _sanitize_origin(origin: Optional[str]) -> Optional[str]:
    if not origin:
        return None
    parsed = urlsplit(origin.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _split_extra_origins(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _build_allowed_origins() -> list[str]:
    raw_origins = [
        FRONTEND_URL,
        FRONTEND_HOMOLOG_URL,
        FRONTEND_HOMOLOG_HTTP_URL,
        BACKEND_BASE_URL,
        *_split_extra_origins(os.getenv("CORS_EXTRA_ORIGINS")),
    ]

    allowed: list[str] = []
    seen = set()

    for origin in raw_origins:
        sanitized = _sanitize_origin(origin)
        if sanitized and sanitized not in seen:
            allowed.append(sanitized)
            seen.add(sanitized)

    if not allowed:
        raise RuntimeError("Nenhuma origem válida configurada para CORS.")

    return allowed


def _should_use_secure_cookie(request: Request) -> bool:
    flag = _parse_bool_env(SESSION_COOKIE_SECURE)
    if flag is not None:
        return flag

    if BACKEND_BASE_URL and BACKEND_BASE_URL.startswith("https://"):
        return True

    return request.url.scheme == "https"

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

# 🔒 CORS autorizado apenas para domínios configurados nos envs
origins = _build_allowed_origins()

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
async def notificar_mensagem_ia(
    data: dict = Body(...)
):
    """
    Recebe notificações do frontend contendo:
    - user_message: comando do usuário
    - mensagem: resposta da IA
    - comando: estrutura bruta retornada pelo n8n
    - tipo: tipo da mensagem (IOT ou general)
    - device: nome do dispositivo
    - action: ação executada
    """

    # 🔍 Log completo do payload recebido
    print("\n[📩 NOVA NOTIFICAÇÃO RECEBIDA]")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # Extrai campos principais
    user_message = data.get("user_message")
    mensagem = data.get("mensagem")
    comando = data.get("comando")
    tipo = data.get("tipo")
    device = data.get("device")
    action = data.get("action")

    print(f"\n[INFO] Tipo: {tipo}")
    print(f"[INFO] Usuário disse: {user_message}")
    print(f"[INFO] Resposta da IA: {mensagem}")
    print(f"[INFO] Dispositivo: {device}")
    print(f"[INFO] Ação: {action}")

    # Se houver comando bruto, tenta converter para objeto
    comando_obj = comando
    if isinstance(comando, str) and comando.strip().startswith(('{', '[')):
        try:
            comando_obj = json.loads(comando)
        except json.JSONDecodeError:
            print(f"[ERRO] JSON inválido em 'comando': {comando}")
            raise HTTPException(status_code=400, detail="Comando JSON inválido")

    # 🚀 Envia o payload completo para o webhook do n8n
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                N8N_LOG_WEBHOOK,
                json={
                    "user_message": user_message,
                    "mensagem": mensagem,
                    "tipo": tipo,
                    "device": device,
                    "action": action,
                    "comando": comando_obj
                }
            )
            print(f"[WEBHOOK N8N] Status: {response.status_code}")
            print(f"[WEBHOOK N8N] Resposta: {response.text}")
    except Exception as e:
        print(f"[ERRO] Falha ao enviar para o webhook N8N: {e}")

    # 🚦 Processa comando IoT localmente se aplicável
    if tipo == "IOT" and comando_obj:
        print(f"[AÇÃO] Enviando comando IoT para execução: {comando_obj}")
        iot_feedback = await processar_resposta(comando_obj)
        return {
            "status": "IOT recebido e enviado ao n8n",
            "device": device,
            "action": action,
            "iot_feedback": iot_feedback or []
        }

    return {
        "status": "Mensagem registrada e enviada ao n8n",
        "user_message": user_message,
        "mensagem": mensagem,
        "device": device,
        "action": action,
        "iot_feedback": []
    }


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
            secure=_should_use_secure_cookie(request),
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
