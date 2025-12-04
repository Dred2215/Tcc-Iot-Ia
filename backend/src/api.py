import json  # manipulação de dados e logs em JSON
import os  # acesso às variáveis de ambiente do sistema
import asyncio # programação assíncrona
import httpx  # cliente HTTP assíncrono para chamar os webhooks do n8n
import aiohttp # cliente HTTP assíncrono para websockets
from pathlib import Path  # manipulação de caminhos de arquivo
from urllib.parse import urlsplit, urlparse  # parsing de URLs para normalização de origens
from fastapi import FastAPI, HTTPException, Response, Request, Body, WebSocket  # core do FastAPI
from fastapi.middleware.cors import CORSMiddleware  # middleware para liberar CORS
from pydantic import BaseModel  # criação de DTOs de request/response pydantic
from contextlib import asynccontextmanager  # gerencia o ciclo de vida (startup/shutdown)
from typing import Optional, Any  # importa o tipo Optional para permitir tipar campos opcionais sem erro
from starlette.websockets import WebSocketState # estados do websocket

from .tratamento_response_IA import inicializar_dispositivos, processar_resposta # lógica de dispositivos


# ==========================
# 🗂️ Carregar variáveis do .env
# ==========================

BASE_DIR = Path(__file__).resolve().parent  # obtém diretório onde o arquivo api.py está localizado
load_env_path = BASE_DIR / ".env"  # caminho para o arquivo .env na mesma pasta
from dotenv import load_dotenv  # carrega variável de ambiente do .env
load_dotenv(load_env_path)  # lê as variáveis do arquivo .env e injeta em os.environ

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
# 🧭 Variáveis de ambiente do projeto
# ==========================

N8N_LOGIN_URL = os.getenv("N8N_LOGIN_URL")  # URL final do fluxo de login do n8n
# Para testes, usamos o webhook fixo em vez de ler da env
N8N_AUTH_CHECK = os.getenv("N8N_AUTH_CHECK")
N8N_LOG_WEBHOOK = os.getenv("N8N_LOG_WEBHOOK")  # webhook de log do n8n
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # base para compor rotas do n8n
WEBHOOK_TEST_BASE_URL = os.getenv("WEBHOOK_TEST_BASE_URL")  # base de testes para compor rotas do n8n
WEBHOOK_RECEIVE_MESSAGE = (
    os.getenv("VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE")
    or os.getenv("WEBHOOK_MESSAGE_CHAT_RESPONSE")
    or os.getenv("WEBHOOK_RECIVE_MESSAGE")
)

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
    print("🔄 [STARTUP] Servidor FastAPI iniciando...")  # loga início do servidor
    print(f"[ENV] Webhook Base URL configurado: {WEBHOOK_BASE_URL}")  # valida leitura da variável
    
    # Inicializa dispositivos Tuya
    try:
        inicializar_dispositivos()
    except Exception as e:
        print(f"⚠️ [STARTUP] Erro ao inicializar dispositivos: {e}")

    yield  # entrega execução para o app rodar
    print("🛑 [SHUTDOWN] Servidor FastAPI finalizando...")  # loga encerramento

app = FastAPI(lifespan=lifespan)  # cria o app principal

# ==========================
# 🌍 Configuração do CORS
# ==========================

dev_origins = [  # origens padrão para desenvolvimento local
    "http://localhost:5173",  # Vite dev server local
    "http://localhost:8080",  # possibilidades comuns de front local
    "http://localhost:4173"
]

env_origins = collect_env_origins()  # coleta todas URLs válidas das envs

final_origins = sorted({*dev_origins, *env_origins})  # une localhosts + origins do .env

print(f"[CORS] Origens permitidas para chamadas externas: {final_origins}")  # loga para debug

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

class VoiceCommand(BaseModel):  # modelo de comando de voz em texto
    message: str  # texto final reconhecido via STT no front

class LoginRequest(BaseModel):  # modelo esperado no login
    email: str  # email a ser enviado pelo frontend
    password: str  # senha a ser enviada pelo frontend

# ==========================
# 🔑 Endpoint: Login do Usuário via n8n
# ==========================

@app.post("/login_user")
async def login_user(request: Request, response: Response, data: LoginRequest):  # endpoint que faz proxy de login para o n8n
    try:
        login_url = f"{WEBHOOK_BASE_URL}/login_user_webhook"  # compõe URL correta do n8n usando a base definida
        print(f"[LOGIN] → Chamando fluxo do n8n em {login_url}")  # loga a URL chamada

        async with httpx.AsyncClient(timeout=10.0) as client:  # cria cliente HTTP assíncrono
            n8n_response = await client.post(
                login_url,  # URL do fluxo de login no n8n
                json={"email": data.email, "password": data.password},  # envia credenciais como JSON no body
            )

        if n8n_response.status_code != 200:  # se a autenticação falhar
            raise HTTPException(status_code=401, detail="❌ Credenciais inválidas no fluxo do n8n")  # devolve 401 ao cliente

        result = n8n_response.json()  # converte resposta do n8n em JSON
        session_id = result.get("session_id")  # extrai ID de sessão retornado

        if not session_id:  # se não retornou session_id
            raise HTTPException(status_code=401, detail="❌ session_id não retornado pelo n8n")  # aborta request

        # salva o session_id como cookie seguro no navegador
        # Esse cookie não pode ser lido via JS (HttpOnly) e só vai em HTTPS se secure=True
        response.set_cookie(
            key="session_id",  # nome do cookie
            value=session_id,  # valor retornado pelo n8n
            httponly=True,  # protege contra acesso JS
            secure=True,  # necessário para permitir SameSite=None em requisições cross-site
            samesite="none",  # permite envio do cookie em chamadas cross-site (frontend ↔ backend)
            max_age=3600,  # dura 1h
        )

        return {"status": "success", "user": result.get("user"), "session_id": session_id}  # retorna login ok para o front

    except Exception as e:  # se algo inesperado acontecer
        print(f"[ERRO LOGIN PROXY] {e}")  # loga o erro
        raise HTTPException(status_code=500, detail=str(e))  # devolve 500 ao cliente


# ==========================
# 🕵️ Endpoint: Verifica sessão do usuário no n8n via cookie
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
        print(f"[AUTH CHECK] session_id recebido. Cookie: {cookie_session}, Header: {header_session}, Query: {query_session}")

        if not session_id:
            raise HTTPException(status_code=401, detail="❌ Cookie de sessão ausente")

        # Envia session_id ao webhook do n8n para validação
        async with httpx.AsyncClient(timeout=10.0) as client:
            n8n_response = await client.get(
                N8N_AUTH_CHECK,
                params={"session_id": session_id},
                headers={"X-Session-Id": session_id},
                cookies={"session_id": session_id},
            )

        # Propaga status/corpo do n8n para o frontend
        content_type = n8n_response.headers.get("content-type", "")
        data = None
        if "application/json" in content_type:
            try:
                data = n8n_response.json()
            except json.JSONDecodeError:
                data = {"raw": n8n_response.text}
        else:
            data = {"raw": n8n_response.text}

        # Loga status e message retornados pelo n8n para debug
        if isinstance(data, dict):
            print(f"[AUTH CHECK] n8n status: {data.get('status')} message: {data.get('message')}")

        if n8n_response.status_code >= 400:
            raise HTTPException(status_code=n8n_response.status_code, detail=data)

        return data

    except HTTPException:
        # Propaga erros HTTP já tratados acima (inclusive 4xx do n8n)
        raise
    except Exception as e:  # se houver falha na request ao n8n
        print(f"[ERRO AUTH CHECK] {e}")  # loga erro
        raise HTTPException(status_code=500, detail="Erro interno ao validar sessão")  # devolve 500

# ==========================
# 🎙️ Endpoint: Envia comando de voz em texto reconhecido
# ==========================

@app.post("/voice_command")
async def voice_command(req: VoiceCommand):  # endpoint que recebe texto final de voz
    try:
        print(f"[🎙️VOZ] Comando final recebido: {req.message}")  # loga input de voz
        return {"status": "ok"}  # resposta simples de ping para o front
    except Exception as e:
        print(f"[ERRO VOZ] {e}")  # loga erro
        raise HTTPException(status_code=500, detail=str(e))  # retorna erro 500

# ==========================
# 🧪 Endpoint: Ping do backend
# ==========================

@app.get("/ping")
async def ping():  # endpoint para testar se o backend está online
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
        print(f"[CHAT] → Encaminhando mensagem para N8N em {webhook_url}")

        # Tenta descobrir a origem: primeiro do body, depois do header
        origin = request.origin or raw_request.headers.get("x-origin") or raw_request.headers.get("origin")
        session_id = raw_request.cookies.get("session_id") or raw_request.headers.get("x-session-id")
        payload = {"comando": request.comando}
        if origin:
            payload["origin"] = origin
        if session_id:
            payload["session_id"] = session_id

        headers = {"X-Origin": origin} if origin else {}
        if session_id:
            headers["X-Session-Id"] = session_id

        # Encaminha para o N8N com cabeçalho opcional de origem
        async with httpx.AsyncClient(timeout=30.0) as client:
            n8n_response = await client.post(
                webhook_url,
                json=payload,
                headers=headers or None,
            )
        
        if n8n_response.status_code != 200:
            print(f"⚠️ [CHAT] Erro N8N: {n8n_response.text}")
            raise HTTPException(status_code=n8n_response.status_code, detail="Erro ao processar mensagem no N8N")

        # Tenta fazer parse do JSON, se falhar retorna texto puro envelopado
        try:
            n8n_json = n8n_response.json()
        except json.JSONDecodeError:
            return {"raw_response": n8n_response.text}

        # Executa comandos IoT localmente, se retornados pelo N8N
        iot_feedback = []
        try:
            iot_feedback = await processar_resposta(n8n_json) or []
        except Exception as e:
            print(f"⚠️ [CHAT] Falha ao processar resposta IoT: {e}")

        # Envelopa o retorno com feedbacks para o frontend
        return {
            "data": n8n_json,
            "iot_feedback": iot_feedback,
        }

    except Exception as e:
        print(f"[ERRO CHAT] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ======================================================
# 👂 WebSocket HOTWORD (aguarda "bob" e encerra)
# ======================================================
@app.websocket("/ws-ping")
async def websocket_ping(websocket: WebSocket):
    """
    WebSocket simples de ping/pong para testar conectividade.
    Envia uma mensagem de confirmação na conexão e ecoa mensagens recebidas.
    """
    await websocket.accept()
    try:
        await websocket.send_text("conectado")
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
    except Exception as e:
        print(f"⚠️ [WS-PING] Erro ou desconexão: {e}")
    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print("🔌 [WS-PING] Conexão encerrada.")


@app.websocket("/ws-hotword")
async def websocket_hotword(websocket: WebSocket):
    await websocket.accept()
    print("👂 [HOTWORD] Cliente conectado")
    await websocket.send_text("✅ Detector ativo. Diga 'bob' para iniciar comando.")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"📩 [HOTWORD] Recebido: {data}")

            if "bob" in data.lower():
                print("🎯 [HOTWORD] Hotword detectada — encerrando conexão.")
                await websocket.send_text("🚀 Hotword detectada: 'bob'")
                await asyncio.sleep(0.3)
                break
            else:
                await websocket.send_text("🗣️ Aguardando hotword...")

    except Exception as e:
        print(f"⚠️ [HOTWORD] Erro ou desconexão: {e}")

    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print("🔌 [HOTWORD] Conexão encerrada.")


# ======================================================
# 🎙️ WebSocket VOICE (envia mensagem ao webhook e executa resposta)
# ======================================================
@app.websocket("/ws-voice")
async def websocket_voice(websocket: WebSocket):
    """
    Recebe o comando completo do frontend e envia para o webhook
    definido em WEBHOOK_RECEIVE_MESSAGE. Depois, envia o retorno para
    o tratamento_response_IA.py, que executa o comando nos dispositivos.
    """
    await websocket.accept()
    print("🎤 [VOICE] Cliente conectado")
    await websocket.send_text("🟢 Conexão de voz estabelecida com o servidor.")

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                # 🗣️ Recebe mensagem do frontend
                data = await websocket.receive_text()
                print(f"📩 [VOICE] Mensagem recebida: {data}")

                if not WEBHOOK_RECEIVE_MESSAGE:
                    await websocket.send_text("⚠️ Nenhum webhook configurado no servidor (WEBHOOK_RECEIVE_MESSAGE).")
                    continue

                session_id = websocket.cookies.get("session_id") or ""

                try:
                    # 🚀 Envia a mensagem ao webhook
                    # Ajustado para usar "comando" para consistência com o módulo de texto
                    async with session.post(
                        f"{WEBHOOK_BASE_URL}/message_input",
                        json={
                            "comando": data,
                            "origin": "voice_module",
                            "session_id": session_id or None,
                        },
                        headers={"X-Session-Id": session_id} if session_id else None,
                        timeout=15,
                    ) as resp:
                        try:
                            # 📡 Tenta decodificar resposta JSON
                            response_json = await resp.json(content_type=None)
                            resposta_formatada = json.dumps(response_json, indent=2, ensure_ascii=False)

                            print(f"📤 [WEBHOOK] Status {resp.status} | Resposta JSON:\n{resposta_formatada}")
                            await websocket.send_text(
                                f"✅ Resposta do webhook ({resp.status}): {resposta_formatada}"
                            )

                            # ⚙️ Envia resposta para tratamento e execução local
                            feedbacks = await processar_resposta(response_json)
                            if feedbacks:
                                for feedback in feedbacks:
                                    mensagem = feedback.get("message")
                                    if mensagem:
                                        await websocket.send_text(mensagem)

                        except Exception:
                            # Caso o retorno não seja JSON, envia texto cru
                            response_text = await resp.text()
                            print(f"📤 [WEBHOOK] Status {resp.status} | Texto:\n{response_text}")
                            await websocket.send_text(
                                f"✅ Resposta do webhook ({resp.status}): {response_text}"
                            )

                except asyncio.TimeoutError:
                    print("⏰ [WEBHOOK] Timeout ao enviar mensagem.")
                    await websocket.send_text("⚠️ O webhook demorou para responder.")
                except Exception as e:
                    print(f"⚠️ [WEBHOOK] Erro ao enviar: {e}")
                    await websocket.send_text(f"⚠️ Erro ao enviar para o webhook: {e}")

    except Exception as e:
        print(f"⚠️ [VOICE] Erro ou desconexão: {e}")

    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print("🔌 [VOICE] Conexão encerrada.")


if __name__ == "__main__":
    import uvicorn  # servidor ASGI para rodar FastAPI
    port = int(os.getenv("PORT", 8000))  # lê porta da env, fallback 8000
    uvicorn.run(app, host="0.0.0.0", port=port)  # sobe servidor garantindo acesso de todas interfaces
