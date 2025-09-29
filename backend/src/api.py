from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Union
import sys
import os

# Adiciona o caminho para importar seu arquivo principal
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Importa a função do seu arquivo principal
from .tratamento_response_IA import teste_chamada_front, processar_resposta

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
    payload: Optional[Union[dict, list]] = None

@app.post("/notificar-mensagem-ia")
async def notificar_mensagem_ia(req: MensagemRequest):
    print(f"[LOG] Recebida notificação com mensagem: {req.mensagem}")  # Log de entrada
    try:
        if req.mensagem:
            teste_chamada_front(req.mensagem)
            print("[LOG] Função teste_chamada_front executada com sucesso.")

        if req.payload is not None:
            print("[LOG] Processando payload recebido da IA...")
            await processar_resposta(req.payload)  # Executa comandos conforme resposta IA

        return {"status": "sucesso", "mensagem": req.mensagem}
    except Exception as e:
        print(f"[LOG] Erro ao executar teste_chamada_front: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
