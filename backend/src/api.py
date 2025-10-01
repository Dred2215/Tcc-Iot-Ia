from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# ✅ Gerenciamento de ciclo de vida com lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Servidor iniciando...")
    print("✅ Backend pronto para receber conexões!")
    yield
    print("🛑 Encerrando aplicação...")
    print("🛑 Backend finalizado com sucesso.")

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
