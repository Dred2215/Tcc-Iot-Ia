import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# ======================================================
# 🌐 CORS
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 👂 WebSocket HOTWORD (simples)
# ======================================================
@app.websocket("/ws-hotword")
async def websocket_hotword(websocket: WebSocket):
    """
    WebSocket simples: aguarda a palavra 'bob' e fecha a conexão.
    """
    await websocket.accept()
    print("👂 [HOTWORD] Cliente conectado")
    await websocket.send_text("✅ Detector ativo. Diga 'bob' para iniciar comando.")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"📩 [HOTWORD] Recebido: {data}")

            if "bob" in data.lower():
                print("🎯 [HOTWORD] Hotword detectada — encerrando conexão.")
                await websocket.send_text("🚀 Hotword detectada: 'bob'")
                await asyncio.sleep(0.3)
                break
            else:
                await websocket.send_text("🗣️ Aguardando hotword...")

    except Exception as e:
        print(f"⚠️ [HOTWORD] Erro ou desconexão: {e}")

    finally:
        await websocket.close()
        print("🔌 [HOTWORD] Conexão encerrada.")


# ======================================================
# 🚀 Execução local
# ======================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
