from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os # Não se esqueça de importar

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Servidor iniciando...")
    # ADICIONE ESTA LINHA PARA DEPURAR
    print(f"✅ VARIÁVEL DE AMBIENTE PORT: {os.getenv('PORT')}") 
    print("✅ Backend pronto para receber conexões!")
    yield
    print("🛑 Encerrando aplicação...")

app = FastAPI(lifespan=lifespan)

# 🔓 CORS aberto (qualquer origem pode acessar)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Endpoint de teste de comunicação
@app.get("/ping")
async def ping():
    return {"message": "Backend está online 🚀"}

# Middleware de log das requisições
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[LOG] {request.method} {request.url}")
    response = await call_next(request)
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
