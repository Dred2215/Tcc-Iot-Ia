import asyncio
import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.tratamento_response_IA import processar_resposta

app = FastAPI()

# 🔒 CORS fixo para homolog - apenas o frontend homolog pode acessar
origins = [
    "https://tcc-iot-frontend-homolog.dlivfa.easypanel.host, http://tcc-iot-frontend-homolog.dlivfa.easypanel.host, https://tcc-iot-backend-homolog.dlivfa.easypanel.host/notificar-mensagem-ia, http://tcc-iot-backend-homolog.dlivfa.easypanel.host/notificar-mensagem-ia"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MensagemRequest(BaseModel):
    mensagem: Optional[str] = ""
    comando: Optional[Any] = ""
    tipo: Optional[str] = ""

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

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
