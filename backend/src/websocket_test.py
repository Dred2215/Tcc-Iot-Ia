import os
import asyncio
import json
import aiohttp
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import uvicorn
from tratamento_response_IA import inicializar_dispositivos, processar_resposta
from starlette.websockets import WebSocketState

# ======================================================
# 🌍 Carrega variáveis de ambiente
# ======================================================
load_dotenv()
WEBHOOK_RECEIVE_MESSAGE = (
    os.getenv("VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE")
    or os.getenv("WEBHOOK_MESSAGE_CHAT_RESPONSE")
    or os.getenv("WEBHOOK_RECIVE_MESSAGE")
)

if not WEBHOOK_RECEIVE_MESSAGE:
    print("⚠️ Aviso: Nenhuma variável de webhook (VITE_WEBHOOK_MESSAGE_CHAT_RESPONSE / WEBHOOK_MESSAGE_CHAT_RESPONSE / WEBHOOK_RECIVE_MESSAGE) foi encontrada no .env.")

app = FastAPI()

# ======================================================
# ⚙️ Inicialização de dispositivos Tuya
# ======================================================
inicializar_dispositivos()

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
# 👂 WebSocket HOTWORD (aguarda "bob" e encerra)
# ======================================================
@app.websocket("/ws-hotword")
async def websocket_hotword(websocket: WebSocket):
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
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print("🔌 [HOTWORD] Conexão encerrada.")


# ======================================================
# 🎙️ WebSocket VOICE (envia mensagem ao webhook e executa resposta)
# ======================================================
@app.websocket("/ws-voice")
async def websocket_voice(websocket: WebSocket):
    """
    Recebe o comando completo do frontend e envia para o webhook
    definido em WEBHOOK_RECIVE_MESSAGE. Depois, envia o retorno para
    o tratamento_response_IA.py, que executa o comando nos dispositivos.
    """
    await websocket.accept()
    print("🎤 [VOICE] Cliente conectado")
    await websocket.send_text("🟢 Conexão de voz estabelecida com o servidor.")

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                # 🗣️ Recebe mensagem do frontend
                data = await websocket.receive_text()
                print(f"📩 [VOICE] Mensagem recebida: {data}")

                if not WEBHOOK_RECEIVE_MESSAGE:
                    await websocket.send_text("⚠️ Nenhum webhook configurado no servidor.")
                    continue

                try:
                    # 🚀 Envia a mensagem ao webhook
                    async with session.post(
                        WEBHOOK_RECEIVE_MESSAGE,
                        json={"message": data},
                        timeout=15,
                    ) as resp:
                        try:
                            # 📡 Tenta decodificar resposta JSON
                            response_json = await resp.json(content_type=None)
                            resposta_formatada = json.dumps(response_json, indent=2, ensure_ascii=False)

                            print(f"📤 [WEBHOOK] Status {resp.status} | Resposta JSON:\n{resposta_formatada}")
                            await websocket.send_text(
                                f"✅ Resposta do webhook ({resp.status}): {resposta_formatada}"
                            )

                            # ⚙️ Envia resposta para tratamento e execução local
                            feedbacks = await processar_resposta(response_json)
                            if feedbacks:
                                for feedback in feedbacks:
                                    mensagem = feedback.get("message")
                                    if mensagem:
                                        await websocket.send_text(mensagem)

                        except Exception:
                            # Caso o retorno não seja JSON, envia texto cru
                            response_text = await resp.text()
                            print(f"📤 [WEBHOOK] Status {resp.status} | Texto:\n{response_text}")
                            await websocket.send_text(
                                f"✅ Resposta do webhook ({resp.status}): {response_text}"
                            )

                except asyncio.TimeoutError:
                    print("⏰ [WEBHOOK] Timeout ao enviar mensagem.")
                    await websocket.send_text("⚠️ O webhook demorou para responder.")
                except Exception as e:
                    print(f"⚠️ [WEBHOOK] Erro ao enviar: {e}")
                    await websocket.send_text(f"⚠️ Erro ao enviar para o webhook: {e}")

    except Exception as e:
        print(f"⚠️ [VOICE] Erro ou desconexão: {e}")

    finally:
        if websocket.application_state != WebSocketState.DISCONNECTED:
            await websocket.close()
        print("🔌 [VOICE] Conexão encerrada.")


# ======================================================
# 🚀 Execução local
# ======================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8008)
