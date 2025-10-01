import asyncio
import json
import os
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

# 👉 Import ajustado (usa src.)
from tratamento_response_IA import processar_resposta

# ✅ Ciclo de vida com logs
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Servidor iniciando...")
    print(f"✅ VARIÁVEL DE AMBIENTE PORT: {os.getenv('PORT')}")
    print("✅ Backend pronto para receber conexões!")
    yield
    print("🛑 Encerrando aplicação...")

app = FastAPI(lifespan=lifespan)

# 🔓 CORS aberto para localhost (ambiente de dev)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
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

# ✅ Endpoint de teste
@app.get("/ping")
async def ping():
    return {"message": "Backend está online 🚀"}

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
