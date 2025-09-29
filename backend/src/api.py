from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import asyncio
import json
from tratamento_response_IA import processar_resposta

# # Importa a função do seu arquivo principal
# from .tratamento_response_IA import teste_chamada_front

app = FastAPI()

# Configuração de CORS com a porta correta do React
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Porta do seu React (Vite)
        "http://127.0.0.1:8080",
        "http://localhost:3000",  # Mantém para testes
        "http://127.0.0.1:3000",
    ],
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

    # Estrutura para armazenar a mensagem e o comando
    class IA:
        message = {
            "message": req.mensagem,
            "command": req.comando
        }

    # Decodifica o comando se ele for uma string JSON
    comando_obj = IA.message["command"]
    if isinstance(comando_obj, str) and comando_obj.strip().startswith(('[', '{')):
        try:
            comando_obj = json.loads(comando_obj)
        except json.JSONDecodeError:
            print(f"[ERRO] Falha ao decodificar o JSON do comando: {comando_obj}")
            raise HTTPException(status_code=400, detail="Comando em formato JSON inválido.")

    # Chama a função para processar o comando da IA
    if req.tipo == "IOT" and comando_obj:
        print(f"[AÇÃO] Executando comando IOT: {comando_obj}")
        # Usamos asyncio.create_task para não bloquear a resposta da API
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