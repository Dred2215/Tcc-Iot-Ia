import asyncio
from typing import Any, Optional

from .dispositivos import Lampada, Portao, SensorPortao
from .config_tuya import get_home_id, get_openapi

# Containers vazios (serão preenchidos na inicialização)
DISPOSITIVOS = {}
CENAS = {}

def inicializar_dispositivos():
    global DISPOSITIVOS, CENAS
    print("🔄 Inicializando dispositivos...")

    openapi = get_openapi()
    home_id = get_home_id()

    DISPOSITIVOS = {
        "lampada": Lampada("Luz", "eb20e4ad6247150831lufg", openapi),
        "sensor_portao": SensorPortao("Sensor Portão", "eba6dbc576c6cb89d0ndap", openapi)  # ✅ novo dispositivo
    }

    CENAS = {
        "portao": Portao("Portão Garagem", openapi, home_id, "yp6IXiAOst5s66wX")
    }

    print("✅ Dispositivo 'Luz' inicializado.")
    print("✅ Dispositivo 'Sensor Portão' inicializado.")
    print("✅ Dispositivo de cena 'Portão Garagem' inicializado.")
    print("✅ Dispositivos e cenas inicializados.")


CORES_TUYA = {
    "vermelho":   {"h": 0,   "s": 1000, "v": 1000},
    "laranja":    {"h": 30,  "s": 1000, "v": 1000},
    "amarelo":    {"h": 60,  "s": 1000, "v": 1000},
    "verde":      {"h": 120, "s": 1000, "v": 1000},
    "ciano":      {"h": 180, "s": 1000, "v": 1000},
    "azul":       {"h": 240, "s": 1000, "v": 1000},
    "roxo":       {"h": 270, "s": 1000, "v": 1000},
    "rosa":       {"h": 300, "s": 1000, "v": 1000},
    "magenta":    {"h": 320, "s": 1000, "v": 1000},
    "branco":     {"h": 0,   "s": 0,    "v": 1000},
    "cinza":      {"h": 0,   "s": 0,    "v": 500},
    "preto":      {"h": 0,   "s": 0,    "v": 0}
}

def formatar_feedback(device_label: str, device_key: str, action: str, resultado: Any) -> Optional[str]:
    nome = device_label or device_key or "dispositivo"

    if device_key == "sensor_portao" and action in {"verificar_estado", "estado_portao"}:
        if isinstance(resultado, bool):
            return f"O portão está {'aberto' if resultado else 'fechado'}."
        if resultado is None:
            return "Não foi possível determinar o estado do portão."

    if isinstance(resultado, bool):
        return f"{nome}: {'ativado' if resultado else 'desativado'}."
    if isinstance(resultado, (int, float, str)):
        return f"{nome}: {resultado}"
    if isinstance(resultado, dict):
        return f"{nome}: {resultado}"
    if isinstance(resultado, list) and resultado:
        return f"{nome}: {resultado}"
    return None


async def executar_comando(idx, cmd):
    device_label = (cmd.get("device") or "").strip()
    device = device_label.lower()
    action = (cmd.get("action") or "").lower()
    action_original = action
    parameter = cmd.get("parameter")
    additional_raw = cmd.get("additional_condit")
    feedback: Optional[str] = None

    # Normaliza additional_condit
    additional = None
    if isinstance(additional_raw, str):
        s = additional_raw.strip().lower()
        if s in ("null", "", "0", "zero"):
            additional = None
        elif s.isdigit():
            additional = int(s)
        else:
            additional = s
    elif isinstance(additional_raw, (int, float)):
        additional = int(additional_raw)

    print(f"[IA] Comando {idx} -> Target: {device}, Action: {action}, Parameter: {parameter}, Delay: {additional}")

    # Resolve alvo
    alvo = None
    alvo_tipo = None
    if device in DISPOSITIVOS:
        alvo = DISPOSITIVOS[device]
        alvo_tipo = "dispositivo"
    elif device in CENAS:
        alvo = CENAS[device]
        alvo_tipo = "cena"

    if alvo is None:
        msg = f"'{device_label or device}' não está configurado."
        print(f"[ERRO] {msg}")
        return {"device": device_label or device, "action": action_original, "message": msg}

    # Delay opcional (não bloqueante)
    if isinstance(additional, int) and additional > 0:
        print(f"Aguardando {additional} segundos antes de executar...")
        await asyncio.sleep(additional)

    # 🔄 Tradução de ações especiais
    if device == "sensor_portao" and action == "verificar_estado":
        action = "estado_portao"

    # 🧩 Nova lógica: Verificação de status específica
    if action == "status" and parameter:
        print(f"🔍 Consultando status específico '{parameter}' do dispositivo '{device}'...")
        res = alvo.status()
        if isinstance(res, dict) and "result" in res:
            for item in res["result"]:
                if item["code"] == parameter:
                    valor = item["value"]
                    msg = f"{device_label or device} → {parameter}: {valor}"
                    print(f"✅ {msg}")
                    return {"device": device_label or device, "action": action_original, "message": msg}
            msg = f"⚠️ Parâmetro '{parameter}' não encontrado no status de '{device_label or device}'."
            print(msg)
            return {"device": device_label or device, "action": action_original, "message": msg}
        else:
            msg = f"❌ Status de '{device_label or device}' não retornou o formato esperado."
            print(msg)
            return {"device": device_label or device, "action": action_original, "message": msg}

    # Executa ação
    if hasattr(alvo, action):
        metodo = getattr(alvo, action)
        try:
            if action == "definir_cor" and isinstance(parameter, str):
                h, s, v = processar_cor(parameter)
                metodo(h, s, v)
            elif parameter is not None and parameter != "":
                metodo(int(parameter))
                feedback = f"Ação '{action_original}' executada em '{device_label or device}'."
            else:
                resultado = metodo()
                if resultado is not None:
                    print(f"📊 Resultado: {resultado}")
                    feedback = formatar_feedback(device_label or device, device, action_original, resultado)
            print(f"[OK] {action} executado em {alvo_tipo} '{device}'.")
        except TypeError as e:
            print(f"[ERRO] Falha ao executar {action} em {device}: {e}")
            feedback = f"Erro ao executar '{action_original}' em '{device_label or device}': {e}"
    else:
        # Fallback
        for fallback in ("executar", "acionar", "play", "run"):
            if hasattr(alvo, fallback):
                try:
                    getattr(alvo, fallback)()
                    print(f"[OK] {fallback} executado em {alvo_tipo} '{device}' (fallback).")
                    feedback = f"Ação '{fallback}' executada em '{device_label or device}'."
                    break
                except Exception as e:
                    print(f"[ERRO] Falha no fallback '{fallback}' para '{device}': {e}")
                    feedback = f"Erro ao executar fallback '{fallback}' em '{device_label or device}': {e}"
        else:
            print(f"[ERRO] Ação '{action}' não encontrada para {alvo_tipo} '{device}'.")
            feedback = f"Ação '{action_original}' não encontrada para '{device_label or device}'."

    return {
        "device": device_label or device,
        "action": action_original,
        "message": feedback,
    }



async def processar_resposta(respostaIA):
    # 🔍 Normaliza entrada
    if isinstance(respostaIA, list):
        iot_cmds = respostaIA

    elif isinstance(respostaIA, dict):
        # Caso 1: Formato novo da IA → {"type": "IOT", "content_message": {...}, "friendly_message": "..."}
        if respostaIA.get("type") == "IOT" and "content_message" in respostaIA:
            iot_cmds = [respostaIA["content_message"]]
            print(f"📦 [NORMALIZAÇÃO] Extraído comando único de 'content_message'.")

        # Caso 2: Formato padrão anterior → {"IOT_command": [ ... ]}
        elif "IOT_command" in respostaIA and isinstance(respostaIA["IOT_command"], list):
            iot_cmds = respostaIA["IOT_command"]
            print(f"📦 [NORMALIZAÇÃO] Extraída lista de 'IOT_command'.")

        # Caso 3: Formato isolado de comando direto
        else:
            iot_cmds = [respostaIA]
            print(f"📦 [NORMALIZAÇÃO] Tratando resposta como comando direto.")

    else:
        print("❌ Nenhuma resposta válida da IA.")
        return []

    if not iot_cmds:
        print("⚠️ Nenhuma ação encontrada.")
        return []

    # 🚀 Executa todos os comandos em paralelo
    tarefas = [executar_comando(idx, cmd) for idx, cmd in enumerate(iot_cmds, start=1)]
    resultados = await asyncio.gather(*tarefas)
    feedbacks = [resultado for resultado in resultados if resultado and resultado.get("message")]
    return feedbacks or []



def processar_cor(nome_cor: str):
    nome_cor = (nome_cor or "").strip().lower()
    if nome_cor in CORES_TUYA:
        c = CORES_TUYA[nome_cor]
        return c["h"], c["s"], c["v"]
    else:
        print(f"[AVISO] Cor '{nome_cor}' não encontrada. Usando branco como padrão.")
        return 0, 0, 1000
