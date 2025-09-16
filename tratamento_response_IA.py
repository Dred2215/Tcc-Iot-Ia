from dispositivos import Lampada, Portao
from config_tuya import openapi, home_id
import time

# Instâncias dos dispositivos
DISPOSITIVOS = {
    "lampada": Lampada("Luz", "eb20e4ad6247150831lufg", openapi)
}

CENAS = {
    "portao": Portao("Portão Garagem", openapi, home_id, "yp6IXiAOst5s66wX")
}

def processar_resposta(respostaIA):
    import time

    # 1) Normaliza a estrutura de entrada
    if isinstance(respostaIA, list):
        # Lista direta
        iot_cmds = respostaIA
    elif isinstance(respostaIA, dict):
        if "IOT_command" in respostaIA and isinstance(respostaIA["IOT_command"], list):
            iot_cmds = respostaIA["IOT_command"]
        else:
            # Se já for um dict de comando único
            iot_cmds = [respostaIA]
    else:
        print("Nenhuma resposta válida da IA.")
        return

    if not iot_cmds:
        print("Nenhuma ação encontrada.")
        return

    # 2) Loop nos comandos normalizados
    for idx, cmd in enumerate(iot_cmds, start=1):
        device = (cmd.get("device") or "").lower()
        action = (cmd.get("action") or "").lower()
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
        else:
            additional = None

        print(f"[IA] Comando {idx} -> Target: {device}, Action: {action}, Condição adicional: {additional}")

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
            continue

        # Delay opcional
        if isinstance(additional, int) and additional > 0:
            print(f"Aguardando {additional} segundos antes de executar...")
            time.sleep(additional)
            additional = None

        # Executa ação
        if hasattr(alvo, action):
            metodo = getattr(alvo, action)
            try:
                if additional is None:
                    metodo()
                else:
                    metodo(additional)
                print(f"[OK] {action} executado em {alvo_tipo} '{device}'.")
            except TypeError:
                metodo()
                print(f"[OK] {action} executado em {alvo_tipo} '{device}' (sem parâmetro).")
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
