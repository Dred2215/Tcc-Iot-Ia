import json  # manipulação de dados e logs em JSON
import os  # acesso às variáveis de ambiente do sistema
import httpx  # cliente HTTP assíncrono para chamar os webhooks do n8n
from pathlib import Path  # manipulação de caminhos de arquivo
from urllib.parse import urlsplit, urlparse  # parsing de URLs para normalização de origens
from fastapi import FastAPI, HTTPException, Response, Request, Body  # core do FastAPI
from fastapi.middleware.cors import CORSMiddleware  # middleware para liberar CORS
from pydantic import BaseModel  # criação de DTOs de request/response pydantic
from contextlib import asynccontextmanager  # gerencia o ciclo de vida (startup/shutdown)
from typing import Optional  # importa o tipo Optional para permitir tipar campos opcionais sem erro


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
N8N_AUTH_CHECK_URL = os.getenv("N8N_AUTH_CHECK_URL")  # URL final do fluxo de verificação de sessão no n8n
N8N_LOG_WEBHOOK = os.getenv("N8N_LOG_WEBHOOK")  # webhook de log do n8n
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # base para compor rotas do n8n

if not WEBHOOK_BASE_URL:  # se faltar a base do n8n
    raise RuntimeError("❌ WEBHOOK_BASE_URL não configurado no backend/src/.env")  # aborta startup

WEBHOOK_BASE_URL = WEBHOOK_BASE_URL.rstrip("/")  # remove "/" do final para evitar duplicar barra ao compor rotas

# ==========================
# ♻️ Ciclo de vida da API
# ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):  # gerencia startup e shutdown
    print("🔄 [STARTUP] Servidor FastAPI iniciando...")  # loga início do servidor
    print(f"[ENV] Webhook Base URL configurado: {WEBHOOK_BASE_URL}")  # valida leitura da variável
    yield  # entrega execução para o app rodar
    print("🛑 [SHUTDOWN] Servidor FastAPI finalizando...")  # loga encerramento

app = FastAPI(lifespan=lifespan)  # cria o app principal

# ==========================
# 🌍 Configuração do CORS
# ==========================

dev_origins = [  # origens padrão para desenvolvimento local
    "http://localhost:5173",  # Vite dev server local
    "http://localhost:8080",  # possibilidades comuns de front local
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
            secure=request.url.scheme == "https",  # só envia em HTTPS se a request do navegador já foi HTTPS
            samesite="lax",  # permite redirects GET normais sem bloquear cookie
            max_age=3600,  # dura 1h
        )

        return {"status": "success", "user": result.get("user")}  # retorna login ok para o front

    except Exception as e:  # se algo inesperado acontecer
        print(f"[ERRO LOGIN PROXY] {e}")  # loga o erro
        raise HTTPException(status_code=500, detail=str(e))  # devolve 500 ao cliente


# ==========================
# 🕵️ Endpoint: Verifica sessão do usuário no n8n via cookie
# ==========================

@app.get("/auth_check_user")
async def auth_check_user(request: Request):  # endpoint para validar cookie de sessão
    try:
        session_id = request.cookies.get("session_id")  # pega o cookie enviado pelo navegador
        print(f"[AUTH CHECK] Cookie recebido: {session_id}")  # loga valor do cookie

        if not session_id:  # se não houver cookie
            raise HTTPException(status_code=401, detail="❌ Cookie de sessão ausente")  # 401: não autenticado

        async with httpx.AsyncClient(timeout=10.0) as client:  # cria cliente HTTP assíncrono
            n8n_response = await client.get(
                f"{N8N_AUTH_CHECK_URL}?session_id={session_id}"  # chama a URL de validação do n8n com o parâmetro de sessão
            )

        if n8n_response.status_code != 200:  # se sessão inválida
            print(
                f"[AUTH CHECK] N8N respondeu {n8n_response.status_code}: {n8n_response.text}"
            )
            raise HTTPException(
                status_code=n8n_response.status_code,
                detail=n8n_response.text or "Sessão inválida/expirada no n8n",
            )

        return {"status": "valid", "data": n8n_response.json()}  # retorna sessão válida

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

if __name__ == "__main__":
    import uvicorn  # servidor ASGI para rodar FastAPI
    port = int(os.getenv("PORT", 8000))  # lê porta da env, fallback 8000
    uvicorn.run(app, host="0.0.0.0", port=port)  # sobe servidor garantindo acesso de todas interfaces
