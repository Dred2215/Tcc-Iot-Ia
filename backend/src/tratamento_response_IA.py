import asyncio
from .dispositivos import Lampada, Portao
from .config_tuya import openapi, home_id

# Instâncias dos dispositivos
DISPOSITIVOS = {
    "lampada": Lampada("Luz", "eb20e4ad6247150831lufg", openapi)
}

CENAS = {
    "portao": Portao("Portão Garagem", openapi, home_id, "yp6IXiAOst5s66wX")
}

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

async def executar_comando(idx, cmd):
    device = (cmd.get("device") or "").lower()
    action = (cmd.get("action") or "").lower()
    parameter = cmd.get("parameter")
    additional_raw = cmd.get("additional_condit")

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
        print(f"[ERRO] '{device}' não encontrado nem em DISPOSITIVOS nem em CENAS.")
        return

    # Delay opcional (não bloqueante!)
    if isinstance(additional, int) and additional > 0:
        print(f"Aguardando {additional} segundos antes de executar...")
        await asyncio.sleep(additional)

    # Executa ação
    if hasattr(alvo, action):
        metodo = getattr(alvo, action)
        try:
            if action == "definir_cor" and isinstance(parameter, str):
                h, s, v = processar_cor(parameter)
                metodo(h, s, v)
            elif action in ("ajustar_brilho", "ajustar_temperatura") and parameter is not None:
                metodo(int(parameter))
            elif parameter is not None:
                metodo(parameter)
            else:
                metodo()
            print(f"[OK] {action} executado em {alvo_tipo} '{device}'.")
        except TypeError as e:
            print(f"[ERRO] Falha ao executar {action} em {device}: {e}")
    else:
        # Fallback
        for fallback in ("executar", "acionar", "play", "run"):
            if hasattr(alvo, fallback):
                try:
                    getattr(alvo, fallback)()
                    print(f"[OK] {fallback} executado em {alvo_tipo} '{device}' (fallback).")
                    break
                except Exception as e:
                    print(f"[ERRO] Falha no fallback '{fallback}' para '{device}': {e}")
        else:
            print(f"[ERRO] Ação '{action}' não encontrada para {alvo_tipo} '{device}'.")


async def processar_resposta(respostaIA):
    # Normaliza entrada
    if isinstance(respostaIA, list):
        iot_cmds = respostaIA
    elif isinstance(respostaIA, dict):
        if "IOT_command" in respostaIA and isinstance(respostaIA["IOT_command"], list):
            iot_cmds = respostaIA["IOT_command"]
        else:
            iot_cmds = [respostaIA]
    else:
        print("Nenhuma resposta válida da IA.")
        return

    if not iot_cmds:
        print("Nenhuma ação encontrada.")
        return

    # Cria e dispara tarefas simultâneas
    tarefas = [executar_comando(idx, cmd) for idx, cmd in enumerate(iot_cmds, start=1)]
    await asyncio.gather(*tarefas)


def processar_cor(nome_cor: str):
    nome_cor = (nome_cor or "").strip().lower()
    if nome_cor in CORES_TUYA:
        c = CORES_TUYA[nome_cor]
        return c["h"], c["s"], c["v"]
    else:
        print(f"[AVISO] Cor '{nome_cor}' não encontrada. Usando branco como padrão.")
        return 0, 0, 1000
