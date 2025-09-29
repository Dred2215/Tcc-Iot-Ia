from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os

# Adiciona o caminho para importar seu arquivo principal
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

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
    comando: Optional[str] = ""
    tipo: Optional[str] = ""

@app.post("/notificar-mensagem-ia")
async def notificar_mensagem_ia(req: MensagemRequest):
    print(f"[LOG] Corpo recebido: mensagem='{req.mensagem}', comando='{req.comando}', tipo='{req.tipo}'")
    print(f"[LOG] Recebida notificação com mensagem: {req.mensagem}")
    print(f"[LOG] Comando recebido: {req.comando}")
    print(f"[LOG] Tipo: {req.tipo}")

    
    
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)