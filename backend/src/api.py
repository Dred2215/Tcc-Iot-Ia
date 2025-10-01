from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

# ✅ Ciclo de vida com logs
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Servidor iniciando...")
    print(f"✅ VARIÁVEL DE AMBIENTE PORT: {os.getenv('PORT')}")
    print("✅ Backend pronto para receber conexões!")
    yield
    print("🛑 Encerrando aplicação...")

app = FastAPI(lifespan=lifespan)

# 🔒 CORS fixo: apenas o frontend homolog pode acessar
origins = [
    "https://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
    "http://tcc-iot-frontend-homolog.dlivfa.easypanel.host",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # só aceita chamadas vindas do frontend homolog
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    port = int(os.getenv("PORT", 8000))  # usa PORT se existir, senão 8000
    uvicorn.run(app, host="0.0.0.0", port=port)
