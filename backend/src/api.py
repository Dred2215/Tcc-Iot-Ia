import json  # manipulação de dados e logs em JSON
import os  # acesso às variáveis de ambiente do sistema
import httpx  # cliente HTTP assíncrono para chamar os webhooks do n8n
from pathlib import Path  # manipulação de caminhos de arquivo
from urllib.parse import urlsplit, urlparse  # parsing de URLs para normalização de origens
from fastapi import Depends, FastAPI, HTTPException, Response, Request, Body, UploadFile, File  # core do FastAPI
from fastapi.middleware.cors import CORSMiddleware  # middleware para liberar CORS
from pydantic import BaseModel, EmailStr  # criação de DTOs de request/response pydantic
from contextlib import asynccontextmanager  # gerencia o ciclo de vida (startup/shutdown)
from typing import Optional, Any  # importa o tipo Optional para permitir tipar campos opcionais sem erro
from sqlalchemy.orm import Session  # sessão de banco por requisição

from .tratamento_response_IA import inicializar_dispositivos, processar_resposta # lógica de dispositivos
from .ai_prompt import BOB_SYSTEM_PROMPT  # system prompt do agente de IA, enviado ao n8n a cada mensagem
from .voice_transcription import TranscriptionError, transcrever_audio_bytes  # transcrição de áudio sob demanda


# ==========================
# 🗂️ Carregar variáveis do .env
# ==========================

# backend/.env e a config real do projeto (nao backend/src/.env, que nao existe).
BASE_DIR = Path(__file__).resolve().parent.parent  # obtém o diretório backend/ (um nível acima de src/)
load_env_path = BASE_DIR / ".env"  # caminho para o arquivo .env em backend/
from dotenv import load_dotenv  # carrega variável de ambiente do .env
load_dotenv(load_env_path)  # lê as variáveis do arquivo .env e injeta em os.environ

# Importado depois do load_dotenv: monta DATABASE_URL/config do Redis a partir da env já carregada.
from .db.session import engine, get_db  # engine e dependency de sessão de banco (SQLAlchemy)
from .redis_session import test_connection as test_redis_connection  # healthcheck do Redis no startup
from .services.auth_service import (  # regras de cadastro e autenticação de usuário
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)
from .services.session_service import create_session, get_session  # sessão de login persistida no Redis

# ==========================
# 🧩 Funções auxiliares
# ==========================

def _sanitize_origin(url: str) -> Optional[str]:  # recebe uma string e tenta converter para um origin válido
    if not isinstance(url, str) or not url.strip():  # se o valor não for string ou for vazio
        return None  # descartamos, não é um origin
    parsed = urlparse(url.strip())  # faz parse da URL removendo espaços
    if parsed.scheme in {"http", "https"} and parsed.netloc:  # precisamos de http(s) + host
        return f"{parsed.scheme}://{parsed.netloc}"  # devolve apenas origin, ex: "https://site.com"
    return None  # se não bateu critério, descartamos

def collect_env_origins() -> list[str]:  # varre TODAS as variáveis de ambiente e captura URLs como origins permitidos
    origins = set()  # conjunto para evitar duplicação
    for value in os.environ.values():  # percorre valores da env
        origin = _sanitize_origin(value)  # tenta limpar e validar URL como origin
        if origin:  # se for válida
            origins.add(origin)  # adiciona ao conjunto
    return sorted(origins)  # retorna lista ordenada

def parse_bool_env(value: Optional[str]) -> bool:  # converte env string para bool
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}  # retorna True se o valor indicar positivo

# ==========================
# 📝 Helper de logging padronizado
# ==========================

def log_event(tag: str, text: str, level: str = "INFO", **context: Any) -> None:
    """
    Imprime logs padronizados com nível, tag e contexto serializado.
    """
    safe_context = {k: v for k, v in context.items() if v is not None}
    try:
        ctx_text = f" | {json.dumps(safe_context, ensure_ascii=False, default=str)}" if safe_context else ""
    except Exception:
        ctx_text = f" | {safe_context}"
    line = f"[{level}] [{tag}] {text}{ctx_text}"
    try:
        print(line)
    except UnicodeEncodeError:
        # Console do Windows (cp1252) nao suporta alguns emojis usados nas mensagens de log;
        # sem esse fallback, o proprio log de erro derruba o handler de excecao.
        print(line.encode("ascii", errors="backslashreplace").decode("ascii"))

# ==========================
# 🧭 Variáveis de ambiente do projeto
# ==========================

# N8N_LOGIN_URL e N8N_AUTH_CHECK nao sao mais usados: login e auth check
# agora autenticam direto no Postgres/Redis (ver /login_user e /auth_check_user).
N8N_LOG_WEBHOOK = os.getenv("N8N_LOG_WEBHOOK")  # webhook de log do n8n
N8N_STATUS_CHECK = os.getenv("N8N_STATUS_CHECK")  # webhook de status usado pelo botão de diagnóstico do frontend
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # base para compor rotas do n8n
WEBHOOK_TEST_BASE_URL = os.getenv("WEBHOOK_TEST_BASE_URL")  # base de testes para compor rotas do n8n

# Shared secret enviado em toda chamada a message_input (carrega comando + prompt).
# Validado no n8n via "Header Auth" no node Webhook de entrada, para impedir
# que a rota seja chamada diretamente por terceiros que descubram a URL.
N8N_INTERNAL_SECRET_HEADER = os.getenv("N8N_INTERNAL_SECRET_HEADER", "X-Internal-Secret")
N8N_INTERNAL_SECRET = os.getenv("N8N_INTERNAL_SECRET")

if not WEBHOOK_BASE_URL:  # se faltar a base do n8n
    raise RuntimeError("❌ WEBHOOK_BASE_URL não configurado no backend/src/.env")  # aborta startup

WEBHOOK_BASE_URL = WEBHOOK_BASE_URL.rstrip("/")  # remove "/" do final para evitar duplicar barra ao compor rotas
# Mantém auth-check no mesmo ambiente do login caso precise reverter para env no futuro
# N8N_AUTH_CHECK_URL = N8N_AUTH_CHECK_URL or f"{WEBHOOK_BASE_URL}/auth_check"

# ==========================
# ♻️ Ciclo de vida da API
# ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):  # gerencia startup e shutdown
    port = int(os.getenv("PORT", 8000))
    log_event("STARTUP", "Servidor FastAPI iniciando...", port=port)
    log_event("STARTUP", "Webhook Base URL configurado", base_url=WEBHOOK_BASE_URL)

    # Testa conexão com o Postgres (SQLAlchemy)
    try:
        with engine.connect():
            log_event("STARTUP", "Status Postgres: OK", port=port)
    except Exception as e:
        log_event("STARTUP", "Status Postgres: FALHA", level="WARN", error=str(e), port=port)

    # Testa conexão com o Redis (sessão de login)
    try:
        redis_ok = test_redis_connection()
        log_event("STARTUP", "Status Redis: OK", ping=redis_ok, port=port)
    except Exception as e:
        log_event("STARTUP", "Status Redis: FALHA", level="WARN", error=str(e), port=port)

    # Inicializa dispositivos Tuya
    try:
        inicializar_dispositivos()
    except Exception as e:
        log_event("STARTUP", "Erro ao inicializar dispositivos", level="WARN", error=str(e))

    log_event("STARTUP", "Servidor FastAPI pronto", port=port)
    yield  # entrega execução para o app rodar
    log_event("SHUTDOWN", "Servidor FastAPI finalizando...", port=port)

app = FastAPI(lifespan=lifespan)  # cria o app principal

# ==========================
# 🌍 Configuração do CORS
# ==========================

dev_origins = [  # origens padrão para desenvolvimento local
    "http://localhost:5173",  # Vite dev server local
    "http://localhost:8080",  # possibilidades comuns de front local
    "http://localhost:4173",
    "http://localhost:8000"
]

env_origins = collect_env_origins()  # coleta todas URLs válidas das envs

final_origins = sorted({*dev_origins, *env_origins})  # une localhosts + origins do .env

log_event("CORS", "Origens permitidas configuradas", origins=final_origins)

app.add_middleware(
    CORSMiddleware,  # ativa middleware de CORS
    allow_origins=final_origins,  # libera todas origens coletadas
    allow_credentials=True,  # permite cookies nas requisições
    allow_methods=["*"],  # libera todos métodos HTTP
    allow_headers=["*"],  # libera todos headers
)

# ==========================
# 🧾 DTOs de request
# ==========================

class LoginRequest(BaseModel):  # modelo esperado no login
    email: str  # email a ser enviado pelo frontend
    password: str  # senha a ser enviada pelo frontend

class RegisterUserRequest(BaseModel):  # modelo esperado no cadastro de usuário
    full_name: str  # nome completo do usuário
    email: EmailStr  # email único, usado no login
    password: str  # senha em texto plano; é hasheada com bcrypt antes de persistir
    phone: Optional[str] = None  # telefone é opcional

# ==========================
# 👤 Endpoint: Criação de Usuário (backend é dono do cadastro)
# ==========================

@app.post("/register_user", status_code=201)
async def register_user_endpoint(data: RegisterUserRequest, db: Session = Depends(get_db)):
    """
    Cria um novo usuário diretamente no Postgres via SQLAlchemy.
    Substitui o fluxo antigo de cadastro via webhook n8n "register-user".
    """
    try:
        user = register_user(
            db,
            full_name=data.full_name,
            email=data.email,
            password=data.password,
            phone=data.phone,
        )
    except EmailAlreadyRegisteredError as e:
        log_event("REGISTER", "Tentativa de cadastro com email já existente", level="WARN", email=data.email)
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        log_event("REGISTER", "Erro inesperado ao cadastrar usuário", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao cadastrar usuário")

    log_event("REGISTER", "Usuário cadastrado com sucesso", user_id=str(user.id), email=user.email)

    return {
        "status": "success",
        "user": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "type": user.type,
        },
    }

# ==========================
# 🔑 Endpoint: Login do Usuário (Postgres + Redis, backend é dono da autenticação)
# ==========================

@app.post("/login_user")
async def login_user(response: Response, data: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica o usuário direto no Postgres (bcrypt) e gera uma sessão no Redis.
    Substitui o fluxo antigo de login via webhook n8n "login_user_webhook".
    """
    try:
        user = authenticate_user(db, email=data.email, password=data.password)
    except InvalidCredentialsError:
        log_event("LOGIN", "Credenciais inválidas", level="WARN", email=data.email)
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    except Exception as e:
        log_event("LOGIN", "Erro inesperado ao autenticar usuário", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao autenticar usuário")

    try:
        session_id = create_session(
            user_id=str(user.id), email=user.email, full_name=user.full_name, user_type=user.type
        )
    except Exception as e:
        log_event("LOGIN", "Erro ao criar sessão no Redis", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao criar sessão")

    # salva o session_id como cookie seguro no navegador
    # Esse cookie não pode ser lido via JS (HttpOnly) e só vai em HTTPS se secure=True
    response.set_cookie(
        key="session_id",  # nome do cookie
        value=session_id,  # valor gerado pelo backend
        httponly=True,  # protege contra acesso JS
        secure=True,  # necessário para permitir SameSite=None em requisições cross-site
        samesite="none",  # permite envio do cookie em chamadas cross-site (frontend ↔ backend)
        max_age=3600,  # dura 1h
    )

    log_event("LOGIN", "Login OK", user_id=str(user.id), user_type=user.type, email=user.email)

    return {
        "status": "success",
        "message": "Login OK",
        "type": user.type,
        "session_id": session_id,
        "user": {"id": str(user.id), "email": user.email},
    }


# ==========================
# 🕵️ Endpoint: Verifica sessão do usuário (Redis, backend é dono da validação)
# ==========================

@app.get("/auth_check_user")
async def auth_check_user(request: Request):  # endpoint para validar cookie de sessão
    try:
        # Coleta session_id de cookie, header ou query para teste
        cookie_session = request.cookies.get("session_id")
        header_session = (request.headers.get("x-session-id") or "").strip()
        raw_auth = (request.headers.get("authorization") or "").strip()
        if not header_session and raw_auth:
            header_session = raw_auth.split(" ", 1)[1].strip() if raw_auth.lower().startswith("bearer ") else raw_auth
        query_session = request.query_params.get("session_id")

        session_id = cookie_session or header_session or query_session
        log_event(
            "AUTH_CHECK",
            "Session recebida para validação",
            cookie=cookie_session,
            header=header_session,
            query=query_session,
        )

        if not session_id:
            log_event("AUTH_CHECK", "Session ausente", level="WARN")
            raise HTTPException(status_code=401, detail="❌ Cookie de sessão ausente")

        session_data = get_session(session_id)
        if not session_data:
            log_event("AUTH_CHECK", "Sessão inválida ou expirada", level="WARN")
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

        data = {
            "status": "success",
            "message": "Sessão válida",
            "type": session_data["type"],
            "session_id": session_id,
            "user": {"id": session_data["id"], "email": session_data["email"]},
        }

        log_event("AUTH_CHECK", "Sessão validada com sucesso", status=data.get("status"))
        return data

    except HTTPException:
        # Propaga erros HTTP já tratados acima
        raise
    except Exception as e:
        log_event("AUTH_CHECK", "Erro interno ao validar sessão", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao validar sessão")  # devolve 500

# ==========================
# 🩺 Endpoint: Proxy do webhook de status do n8n (sonda de diagnóstico do frontend)
# ==========================

@app.get("/status_check")
async def status_check():  # endpoint que faz proxy do botão de status do frontend para o webhook do n8n
    if not N8N_STATUS_CHECK:
        raise HTTPException(status_code=500, detail="N8N_STATUS_CHECK não configurado no backend/.env")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            n8n_response = await client.get(N8N_STATUS_CHECK)

        content_type = n8n_response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                data = n8n_response.json()
            except json.JSONDecodeError:
                data = {"raw": n8n_response.text}
        else:
            data = {"raw": n8n_response.text}

        log_event("STATUS_CHECK", "Resposta do webhook de status", status_code=n8n_response.status_code)

        return {
            "status": "success" if n8n_response.status_code < 400 else "error",
            "http_status": n8n_response.status_code,
            "data": data,
        }
    except Exception as e:
        log_event("STATUS_CHECK", "Erro ao consultar webhook de status", level="ERROR", error=str(e))
        raise HTTPException(status_code=502, detail=f"Erro ao consultar webhook de status: {e}")

# ==========================
# 🎙️ Endpoint: Transcrição de áudio gravado (substitui os WebSockets de voz)
# ==========================

@app.post("/voice_transcribe")
async def voice_transcribe(audio: UploadFile = File(...)):
    """
    Recebe um arquivo de áudio gravado no navegador (MediaRecorder API),
    transcreve usando o Google Speech Recognition público e devolve o texto.
    O frontend usa esse texto no mesmo fluxo de chat de texto (/message_input).
    """
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")

        texto = transcrever_audio_bytes(audio_bytes, filename_hint=audio.filename or "audio.webm")
        log_event("VOICE_TRANSCRIBE", "Áudio transcrito com sucesso", transcribed_text=texto)
        return {"status": "success", "text": texto}

    except TranscriptionError as e:
        log_event("VOICE_TRANSCRIBE", "Falha ao transcrever áudio", level="WARN", error=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        log_event("VOICE_TRANSCRIBE", "Erro interno ao transcrever áudio", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao transcrever áudio")

# ==========================
# 🧪 Endpoint: Ping do backend
# ==========================

@app.get("/ping")
async def ping():  # endpoint para testar se o backend está online
    log_event("PING", "Healthcheck solicitado")
    return {"message": "Backend está online 🚀"}  # indica que o backend está respondendo corretamente


# ==========================
# 💬 DTOs para Chat
# ==========================
class ChatRequest(BaseModel):
    # Permite texto ou payload estruturado vindo do frontend/N8N
    comando: Any
    origin: Optional[str] = None

# ==========================
# 📨 Endpoint: Proxy de Chat (Texto)
# ==========================
@app.post("/message_input")
async def chat_message_proxy(request: ChatRequest, raw_request: Request):
    """
    Recebe a mensagem de texto do frontend e encaminha para o webhook do N8N.
    """
    try:
        webhook_url = f"{WEBHOOK_BASE_URL}/message_input"
        log_event("CHAT", "Encaminhando mensagem para N8N", url=webhook_url)

        # Tenta descobrir a origem: primeiro do body, depois do header
        origin = request.origin or raw_request.headers.get("x-origin") or raw_request.headers.get("origin")
        session_id = raw_request.cookies.get("session_id") or raw_request.headers.get("x-session-id")

        # O backend valida a sessão no Redis próprio ANTES de repassar ao n8n.
        # O n8n não tem acesso a esse Redis, então não precisa (nem deve) validar sessão.
        if not session_id or not get_session(session_id):
            log_event("CHAT", "Sessão ausente ou inválida", level="WARN")
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")

        # O backend é o dono do system prompt do agente (Bob); o n8n recebe
        # o prompt já pronto e o repassa para o node AI Agent como system prompt.
        payload = {"comando": request.comando, "prompt": BOB_SYSTEM_PROMPT}
        if origin:
            payload["origin"] = origin
        if session_id:
            payload["session_id"] = session_id

        headers = {"X-Origin": origin} if origin else {}
        if session_id:
            headers["X-Session-Id"] = session_id
        if N8N_INTERNAL_SECRET:
            headers[N8N_INTERNAL_SECRET_HEADER] = N8N_INTERNAL_SECRET

        # Encaminha para o N8N com cabeçalho opcional de origem
        async with httpx.AsyncClient(timeout=30.0) as client:
            n8n_response = await client.post(
                webhook_url,
                json=payload,
                headers=headers or None,
            )
        
        if n8n_response.status_code != 200:
            log_event("CHAT", "Erro retornado pelo N8N", level="WARN", status_code=n8n_response.status_code, body=n8n_response.text)
            raise HTTPException(status_code=n8n_response.status_code, detail="Erro ao processar mensagem no N8N")

        # Tenta fazer parse do JSON, se falhar retorna texto puro envelopado
        try:
            n8n_json = n8n_response.json()
        except json.JSONDecodeError:
            return {"raw_response": n8n_response.text}

        # O n8n pode responder um dict direto ou um array com um único item;
        # normaliza para checar o "type" independente do formato recebido.
        n8n_item = n8n_json[0] if isinstance(n8n_json, list) and n8n_json else n8n_json

        # Se for resposta geral, apenas devolve para o frontend sem processar IoT
        if isinstance(n8n_item, dict) and str(n8n_item.get("type")).lower() == "general":
            return {
                "data": n8n_json,
                "iot_feedback": [],
            }

        # Executa comandos IoT localmente, se retornados pelo N8N
        iot_feedback = []
        try:
            iot_feedback = await processar_resposta(n8n_json) or []
        except Exception as e:
            log_event("CHAT", "Falha ao processar resposta IoT", level="WARN", error=str(e))
        else:
            log_event("CHAT", "Processamento IoT concluído", feedbacks=len(iot_feedback))

        # Envelopa o retorno com feedbacks para o frontend
        return {
            "data": n8n_json,
            "iot_feedback": iot_feedback,
        }

    except HTTPException:
        # Propaga erros HTTP já tratados acima (ex: 401 de sessão inválida, 4xx/5xx do n8n)
        raise
    except Exception as e:
        log_event("CHAT", "Erro interno ao processar chat", level="ERROR", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn  # servidor ASGI para rodar FastAPI
    port = int(os.getenv("PORT", 8000))  # lê porta da env, fallback 8000
    uvicorn.run(app, host="0.0.0.0", port=port)  # sobe servidor garantindo acesso de todas interfaces
