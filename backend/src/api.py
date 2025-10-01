import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.tratamento_response_IA import inicializar_dispositivos, processar_resposta


app = FastAPI()

@app.on_event("startup")
async def startup_event():
    print("🔄 Inicializando dispositivos...")
    inicializar_dispositivos()
    print("✅ Dispositivos e cenas inicializados.")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛑 Encerrando aplicação...")


# 🔓 CORS aberto - aceita qualquer origem enviada no header Origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # aceita todos os domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MensagemRequest(BaseModel):
    mensagem: Optional[str] = ""
    comando: Optional[Any] = ""
    tipo: Optional[str] = ""

# ✅ Endpoint de notificação
@app.post("/notificar-mensagem-ia")
async def notificar_mensagem_ia(req: MensagemRequest):
    print(f"[LOG] Corpo recebido: mensagem='{req.mensagem}', comando='{req.comando}', tipo='{req.tipo}'")

    class IA:
        message = {
            "message": req.mensagem,
            "command": req.comando
        }

    comando_obj = IA.message["command"]
    if isinstance(comando_obj, str) and comando_obj.strip().startswith(('[', '{')):
        try:
            comando_obj = json.loads(comando_obj)
        except json.JSONDecodeError:
            print(f"[ERRO] Falha ao decodificar o JSON do comando: {comando_obj}")
            raise HTTPException(status_code=400, detail="Comando em formato JSON inválido.")

    if req.tipo == "IOT" and comando_obj:
        print(f"[AÇÃO] Executando comando IOT: {comando_obj}")
        asyncio.create_task(processar_resposta(comando_obj))
        return {"status": "Comando IOT recebido e sendo processado em segundo plano."}

    return {"status": "Notificação recebida", "data": IA.message}

# ✅ Endpoint de teste de comunicação
@app.get("/ping")
async def ping():
    return {"message": "Backend está online e se comunicando com o frontend 🚀"}

# Middleware de log
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
