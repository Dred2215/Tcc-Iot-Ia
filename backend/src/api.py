import asyncio  # usado para operações assíncronas, se necessário no futuro
import json  # usado para manipular JSON (logs, parsing de comandos)
import os  # usado para acessar variáveis de ambiente
import httpx  # cliente HTTP assíncrono para chamar webhooks do n8n
from datetime import datetime, timezone  # pode ser usado para timestamps se necessário
from pathlib import Path  # usado para resolver caminhos de arquivos (como .env)
from urllib.parse import urlsplit  # usado para quebrar URLs e extrair origem (scheme + host)
from uuid import uuid4  # importado caso precise gerar IDs únicos
from typing import Any, Optional  # tipos opcionais para anotações
from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Request, Body  # componentes principais do FastAPI
from fastapi.middleware.cors import CORSMiddleware  # middleware de CORS para liberar domínios
from pydantic import BaseModel  # base para modelos de request/response
from contextlib import asynccontextmanager  # usado para gerenciar ciclo de vida (lifespan) da aplicação
from dotenv import load_dotenv  # carrega variáveis de ambiente do arquivo .env

# 👉 Import ajustado (usa src.)
BASE_DIR = Path(__file__).resolve().parent  # pega a pasta onde está o api.py (backend/src)
load_dotenv(BASE_DIR / ".env")  # carrega o arquivo .env localizado em backend/src/.env

from .tratamento_response_IA import processar_resposta, inicializar_dispositivos, DISPOSITIVOS  # funções e estrutura de dispositivos IoT

# ==========================
# 🔐 Leitura das variáveis .env
# ==========================

N8N_LOGIN_URL = os.getenv("N8N_LOGIN_URL")  # URL do webhook de login no n8n
N8N_AUTH_CHECK_URL = os.getenv("N8N_AUTH_CHECK_URL")  # URL do webhook de validação de sessão no n8n
N8N_LOG_WEBHOOK = os.getenv("N8N_LOG_WEBHOOK")  # URL do webhook de log de mensagens no n8n

WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # URL base dos webhooks principais do n8n
WEBHOOK_TEST_BASE_URL = os.getenv("WEBHOOK_TEST_BASE_URL")  # URL base dos webhooks de teste do n8n

FRONTEND_URL = os.getenv("FRONTEND_URL")  # URL principal do frontend em produção/homolog
FRONTEND_HOMOLOG_HTTP_URL = os.getenv("FRONTEND_HOMOLOG_HTTP_URL")  # URL HTTP do frontend em homologação

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL") or os.getenv("BACKEND_URL")  # URL base do backend atual
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE")  # flag opcional para forçar secure nos cookies de sessão

VITE_VOICE_WS_BASE = os.getenv("VITE_VOICE_WS_BASE")  # endpoint base do WebSocket de voz
VITE_VOICE_WS_PORT = os.getenv("VITE_VOICE_WS_PORT")  # porta usada para o WebSocket de voz

TUYA_ENDPOINT = os.getenv("TUYA_ENDPOINT")  # endpoint da API da Tuya (IoT)

CORS_EXTRA_ORIGINS = os.getenv("CORS_EXTRA_ORIGINS")  # lista opcional de origens extras para CORS (separadas por vírgula)

# ==========================
# 🔧 Helpers de configuração
# ==========================

def _parse_bool_env(value: Optional[str]) -> Optional[bool]:  # converte uma env string em booleano, se existir
    if value is None:  # se a variável não foi definida
        return None  # retorna None para indicar ausência
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}  # retorna True se estiver em um dos valores aceitos


def _sanitize_origin(origin: Optional[str]) -> Optional[str]:  # normaliza uma string para o formato origin "scheme://host"
    if not origin:  # se for None ou string vazia
        return None  # retorna None (não é um origin válido)
    parsed = urlsplit(origin.strip())  # quebra a URL em partes (scheme, netloc, path, etc.)
    if not parsed.scheme or not parsed.netloc:  # precisa ao menos de esquema (http/https) e host
        return None  # se faltar algo, descartamos
    return f"{parsed.scheme}://{parsed.netloc}"  # devolve apenas scheme://host (sem path, query, etc.)


def _split_extra_origins(raw: Optional[str]) -> list[str]:  # separa uma lista de origens extra vindo de uma env
    if not raw:  # se não houver nada configurado
        return []  # retorna lista vazia
    return [item.strip() for item in raw.split(",") if item.strip()]  # divide por vírgula e remove espaços/itens vazios


def collect_env_origins() -> list[str]:  # varre TODAS as variáveis de ambiente e coleta qualquer URL como origin
    origins: set[str] = set()  # conjunto para evitar origens duplicadas
    for env_value in os.environ.values():  # percorre todos os valores de variáveis de ambiente
        if not isinstance(env_value, str) or not env_value:  # ignora valores não-string ou vazios
            continue  # segue para o próximo
        fragments: list[str] = []  # lista de pedaços de texto a serem avaliados
        for chunk in env_value.split(","):  # divide por vírgula para suportar listas em uma única env
            fragments.extend(chunk.split())  # divide também por espaço para capturar casos separados por espaço
        if not fragments:  # se mesmo assim não tiver fragmentos
            fragments = [env_value]  # considera o valor inteiro como um fragmento
        for fragment in fragments:  # avalia cada pedaço individualmente
            origin = _sanitize_origin(fragment)  # tenta normalizar o fragmento para origin válido
            if origin:  # se resultou em origin válido (http(s) com host)
                origins.add(origin)  # adiciona ao conjunto
    return sorted(origins)  # retorna lista ordenada de origens únicas


# Origens padrão de desenvolvimento (úteis para testes locais)
DEFAULT_DEV_ORIGINS = [  # lista de origens liberadas por padrão para ambiente de desenvolvimento
    "http://localhost:8000",  # backend local
    "http://localhost:8080",  # frontend em dev comum
    "http://localhost:5173",  # Vite em dev
]


def build_allowed_origins() -> list[str]:  # monta a lista final de origens permitidas para CORS
    raw_origins: set[str] = set()  # conjunto para acumular origens "cruas"

    # 🔹 Origens fixas de desenvolvimento
    raw_origins.update(DEFAULT_DEV_ORIGINS)  # adiciona localhosts padrão para desenvolvimento

    # 🔹 Origens principais explícitas do .env (caso existam)
    raw_origins.update(
        filter(
            None,
            [
                FRONTEND_URL,  # URL completa do frontend principal
                FRONTEND_HOMOLOG_HTTP_URL,  # URL HTTP do frontend em homologação
                BACKEND_BASE_URL,  # URL base do backend
                WEBHOOK_BASE_URL,  # URL base dos webhooks do n8n
                WEBHOOK_TEST_BASE_URL,  # URL base dos webhooks de teste do n8n
                N8N_LOGIN_URL,  # URL do webhook de login
                N8N_AUTH_CHECK_URL,  # URL do webhook de validação de sessão
                N8N_LOG_WEBHOOK,  # URL do webhook de logs
                VITE_VOICE_WS_BASE,  # endpoint de WebSocket (pode aparecer em origem, mesmo que não seja obrigatório)
                TUYA_ENDPOINT,  # endpoint de API da Tuya (normalmente server→server, mas incluímos por segurança)
            ],
        )
    )

    # 🔹 Origens extras definidas manualmente em CORS_EXTRA_ORIGINS
    raw_origins.update(_split_extra_origins(CORS_EXTRA_ORIGINS))  # adiciona qualquer origem extra definida em env

    # 🔹 Origens detectadas automaticamente em QUALQUER variável de ambiente
    env_detected = collect_env_origins()  # coleta origens a partir de todos os valores de env que forem URLs
    raw_origins.update(env_detected)  # junta essas origens detectadas ao conjunto principal

    allowed: list[str] = []  # lista final de origens normalizadas e sem duplicação
    seen: set[str] = set()  # conjunto para rastrear quais já foram adicionadas

    for origin in raw_origins:  # percorre todas as origens cruas coletadas
        sanitized = _sanitize_origin(origin)  # normaliza e valida cada origem individualmente
        if sanitized and sanitized not in seen:  # se for válida e ainda não estiver na lista
            allowed.append(sanitized)  # adiciona à lista final
            seen.add(sanitized)  # marca como já vista

    if not allowed:  # se, ao final, nenhuma origem restar
        raise RuntimeError("Nenhuma origem válida configurada para CORS.")  # impede que a aplicação suba sem CORS configurado

    print(f"[CORS] Origens permitidas: {allowed}")  # loga as origens finais para depuração
    return allowed  # retorna a lista final para uso no middleware


def _should_use_secure_cookie(request: Request) -> bool:  # decide se o cookie de sessão deve ser marcado como 'secure'
    flag = _parse_bool_env(SESSION_COOKIE_SECURE)  # tenta ler a preferência do .env
    if flag is not None:  # se a env foi definida explicitamente
        return flag  # usa o valor definido na env

    if BACKEND_BASE_URL and BACKEND_BASE_URL.startswith("https://"):  # se a URL base do backend usa HTTPS
        return True  # força cookie como secure

    return request.url.scheme == "https"  # caso contrário, decide baseado no esquema da requisição atual

# ==========================
# 🚀 Inicialização da aplicação
# ==========================

@asynccontextmanager
async def lifespan(app: FastAPI):  # gerencia o ciclo de vida da aplicação FastAPI
    print("🔄 Servidor iniciando...")  # log de inicialização
    print(f"✅ VARIÁVEL DE AMBIENTE PORT: {os.getenv('PORT')}")  # mostra qual porta está configurada

    # 🚀 Inicializa os dispositivos/cenas aqui
    try:
        inicializar_dispositivos()  # carrega e prepara os dispositivos IoT e cenas
        print("[INIT] Dispositivos e cenas prontos:", list(DISPOSITIVOS.keys()))  # lista os dispositivos/cenas disponíveis
    except Exception as e:
        print(f"[ERRO] Falha ao inicializar dispositivos/cenas: {e}")  # loga erro caso algo dê errado na inicialização

    print("✅ Backend pronto para receber conexões!")  # indica que o backend está pronto
    yield  # entrega o controle para o servidor FastAPI rodar normalmente
    print("🛑 Encerrando aplicação...")  # log quando a aplicação estiver sendo finalizada

app = FastAPI(lifespan=lifespan)  # cria a instância principal da aplicação FastAPI com o lifespan configurado

# ==========================
# 🔒 Configuração de CORS
# ==========================

ALLOWED_ORIGINS = build_allowed_origins()  # monta a lista final de origens permitidas para CORS com base nas envs + localhost

app.add_middleware(  # adiciona o middleware de CORS à aplicação
    CORSMiddleware,  # usa o middleware padrão da FastAPI/Starlette
    allow_origins=ALLOWED_ORIGINS,  # define quais origens podem fazer requisições ao backend
    allow_credentials=True,  # permite envio de cookies/autenticação nas requisições (necessário para login com sessão)
    allow_methods=["*"],  # libera todos os métodos HTTP (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # libera todos os cabeçalhos (incluindo Authorization, Content-Type, etc.)
)

# ==========================
# 🌐 Modelos e Endpoints
# ==========================

# ✅ Modelo da request de mensagem
class MensagemRequest(BaseModel):  # modelo pydantic para requests relacionadas à mensagem da IA
    mensagem: Optional[str] = ""  # texto da mensagem retornada pela IA
    comando: Optional[Any] = ""  # comando cru que pode vir da IA/n8n
    tipo: Optional[str] = ""  # tipo da mensagem (por exemplo: "IOT" ou "general")

# ✅ Endpoint de notificação
@app.post("/notificar-mensagem-ia")
async def notificar_mensagem_ia(
    data: dict = Body(...),  # corpo da requisição recebido como dicionário genérico
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
    print("\n[📩 NOVA NOTIFICAÇÃO RECEBIDA]")  # marca visualmente o início de uma nova notificação
    print(json.dumps(data, indent=2, ensure_ascii=False))  # imprime o JSON recebido de forma legível

    # Extrai campos principais
    user_message = data.get("user_message")  # pega a mensagem original do usuário
    mensagem = data.get("mensagem")  # pega a resposta da IA
    comando = data.get("comando")  # pega o comando bruto retornado pela IA/n8n
    tipo = data.get("tipo")  # pega o tipo de mensagem (IOT ou geral)
    device = data.get("device")  # pega o nome do dispositivo envolvido
    action = data.get("action")  # pega a ação executada

    print(f"\n[INFO] Tipo: {tipo}")  # loga o tipo da mensagem
    print(f"[INFO] Usuário disse: {user_message}")  # loga a mensagem original do usuário
    print(f"[INFO] Resposta da IA: {mensagem}")  # loga a resposta da IA
    print(f"[INFO] Dispositivo: {device}")  # loga o dispositivo associado
    print(f"[INFO] Ação: {action}")  # loga a ação executada

    # Se houver comando bruto, tenta converter para objeto
    comando_obj = comando  # começa assumindo o comando como foi recebido
    if isinstance(comando, str) and comando.strip().startswith(('{', '[')):  # se o comando for string JSON
        try:
            comando_obj = json.loads(comando)  # tenta converter para objeto Python
        except json.JSONDecodeError:
            print(f"[ERRO] JSON inválido em 'comando': {comando}")  # log de erro em caso de JSON inválido
            raise HTTPException(status_code=400, detail="Comando JSON inválido")  # retorna erro HTTP 400 para o cliente

    # 🚀 Envia o payload completo para o webhook do n8n
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:  # cria cliente HTTP assíncrono com timeout de 10s
            response = await client.post(
                N8N_LOG_WEBHOOK,  # URL do webhook de log no n8n
                json={
                    "user_message": user_message,  # mensagem original do usuário
                    "mensagem": mensagem,  # resposta da IA
                    "tipo": tipo,  # tipo da mensagem
                    "device": device,  # dispositivo
                    "action": action,  # ação
                    "comando": comando_obj,  # comando estruturado (objeto)
                },
            )
            print(f"[WEBHOOK N8N] Status: {response.status_code}")  # loga o status HTTP da chamada ao n8n
            print(f"[WEBHOOK N8N] Resposta: {response.text}")  # loga o corpo da resposta do n8n
    except Exception as e:
        print(f"[ERRO] Falha ao enviar para o webhook N8N: {e}")  # loga qualquer erro de rede ou conexão com o n8n

    # 🚦 Processa comando IoT localmente se aplicável
    if tipo == "IOT" and comando_obj:  # se o tipo for IOT e houver comando para tratar
        print(f"[AÇÃO] Enviando comando IoT para execução: {comando_obj}")  # loga o comando IoT
        iot_feedback = await processar_resposta(comando_obj)  # chama o processador IoT para executar o comando
        return {
            "status": "IOT recebido e enviado ao n8n",  # status descritivo do fluxo
            "device": device,  # devolve o dispositivo envolvido
            "action": action,  # devolve a ação executada
            "iot_feedback": iot_feedback or [],  # retorno do processamento IoT (ou lista vazia)
        }

    return {
        "status": "Mensagem registrada e enviada ao n8n",  # status padrão para mensagens não IoT
        "user_message": user_message,  # devolve a mensagem original
        "mensagem": mensagem,  # devolve a resposta da IA
        "device": device,  # devolve o dispositivo
        "action": action,  # devolve a ação
        "iot_feedback": [],  # sem feedback IoT neste caso
    }


# ✅ Endpoint para comandos de voz (texto final do WebSocket)
class VoiceCommand(BaseModel):  # modelo para requests de comando de voz
    message: str  # texto final reconhecido depois do STT

@app.post("/voice_command")
async def voice_command(req: VoiceCommand):  # endpoint que recebe comandos de voz em texto
    """
    Recebe o texto final reconhecido pela voz e envia para o sistema de tratamento.
    """
    try:
        print(f"[🎙️ VOICE] Comando recebido: {req.message}")  # loga o texto do comando de voz

        # 🔹 Envia o texto para o mesmo fluxo usado no chat textual
        resposta = await processar_resposta(req.message)  # processa o comando usando a mesma lógica da IA

        print(f"[🎯 VOICE] Resposta gerada: {resposta}")  # loga a resposta gerada
        return {"status": "ok", "response": resposta}  # retorna status OK e resposta para o frontend

    except Exception as e:
        print(f"[ERRO VOICE] {e}")  # loga o erro ocorrido no processamento
        raise HTTPException(status_code=500, detail=str(e))  # devolve erro HTTP 500 para o cliente


# ✅ Endpoint de teste simples
@app.get("/ping")
async def ping():  # endpoint de teste para verificar se o backend está online
    return {"message": "Backend está online 🚀"}  # retorna mensagem simples de status

class LoginRequest(BaseModel):  # modelo de request para login de usuário
    email: str  # email de login
    password: str  # senha de login

@app.post("/login_user")
async def login_user(request: Request, response: Response, data: LoginRequest):  # endpoint de login
    """
    Endpoint seguro de login.
    Chama o webhook n8n de login e grava o session_id como cookie HttpOnly.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:  # cliente HTTP assíncrono com timeout
            n8n_response = await client.post(
                N8N_LOGIN_URL,  # URL do webhook de login no n8n
                json={"email": data.email, "password": data.password},  # corpo com email e senha
            )

        if n8n_response.status_code != 200:  # se o n8n retornar status diferente de 200
            raise HTTPException(status_code=401, detail=f"Erro N8N: {n8n_response.status_code}")  # devolve 401 para o cliente

        result = n8n_response.json()  # interpreta a resposta do n8n como JSON
        print("[N8N LOGIN RESULT]", result)  # loga o resultado

        session_id = result.get("session_id")  # extrai session_id retornado pelo n8n
        if not session_id:  # se o n8n não retornou session_id
            raise HTTPException(status_code=401, detail="Login sem session_id retornado")  # devolve erro para o cliente

        # Define cookie HttpOnly (TTL já gerenciado pelo n8n/Redis)
        response.set_cookie(
            key="session_id",  # nome do cookie
            value=session_id,  # valor do cookie (session_id)
            httponly=True,  # impede acesso ao cookie via JavaScript
            secure=_should_use_secure_cookie(request),  # marca como secure se HTTPS estiver em uso
            samesite="lax",  # política de SameSite mais permissiva para navegação normal
            max_age=3600,  # tempo de vida em segundos (1 hora)
        )

        return {"status": "success", "user": result.get("user")}  # retorna status de sucesso e dados do usuário

    except Exception as e:
        print(f"[ERRO LOGIN_USER] {e}")  # loga qualquer erro no processo de login
        raise HTTPException(status_code=500, detail=str(e))  # devolve erro HTTP genérico 500

@app.get("/auth_check_user")
async def auth_check_user(request: Request):  # endpoint para validar a sessão do usuário
    """
    Valida o cookie de sessão com o webhook n8n.
    """
    try:
        session_id = request.cookies.get("session_id")  # pega o cookie de sessão enviado pelo navegador
        if not session_id:  # se não houver cookie de sessão
            raise HTTPException(status_code=401, detail="Cookie de sessão ausente")  # devolve 401

        async with httpx.AsyncClient(timeout=10.0) as client:  # cliente HTTP assíncrono
            n8n_response = await client.get(f"{N8N_AUTH_CHECK_URL}?session_id={session_id}")  # chama o n8n para validar sessão

        if n8n_response.status_code != 200:  # se a sessão for inválida/expirada
            raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")  # devolve 401

        data = n8n_response.json()  # interpreta a resposta do n8n como JSON
        return {"status": "valid", "data": data}  # devolve status válido e os dados retornados pelo n8n

    except Exception as e:
        print(f"[ERRO AUTH_CHECK] {e}")  # loga erro ocorrido na validação
        raise HTTPException(status_code=500, detail=str(e))  # devolve erro genérico 500

# Middleware de log
@app.middleware("http")
async def log_requests(request: Request, call_next):  # middleware que loga todas as requisições HTTP
    print(f"[LOG] {request.method} {request.url}")  # imprime método e URL da requisição
    response = await call_next(request)  # prossegue com o processamento normal da requisição
    return response  # devolve a resposta para o cliente

if __name__ == "__main__":  # bloco para executar o servidor diretamente via python api.py
    import uvicorn  # servidor ASGI usado para subir o FastAPI
    port = int(os.getenv("PORT", 8000))  # lê a porta da env ou usa 8000 como padrão
    uvicorn.run(app, host="0.0.0.0", port=port)  # inicia o servidor escutando em todas as interfaces de rede
