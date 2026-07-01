"""
Script de diagnostico da integracao Tuya.

Testa a conexao com a Tuya OpenAPI usando TUYA_ACCESS_ID/TUYA_ACCESS_SECRET
e tenta listar os dispositivos da conta, mesmo sem TUYA_UID/TUYA_HOME_ID
configurados (nesse caso, ajuda a descobrir esses valores).
"""

from ..core import config_tuya


def _print_devices(devices: list) -> None:
    if not devices:
        print("  (nenhum dispositivo encontrado)")
        return
    for device in devices:
        name = device.get("name") or device.get("custom_name") or "(sem nome)"
        device_id = device.get("id") or device.get("device_id")
        online = device.get("online")
        category = device.get("category")
        print(f"  - {name} | id={device_id} | categoria={category} | online={online}")


def main() -> None:
    print("[TUYA] Conectando na Tuya OpenAPI...")
    try:
        api = config_tuya.get_openapi()
    except Exception as e:
        print(f"[TUYA] Falha ao conectar: {e}")
        return

    print("[TUYA] Conexao OK (autenticado).")

    uid = config_tuya.get_uid()
    home_id = None
    try:
        home_id = config_tuya.get_home_id()
    except Exception:
        pass

    # Se nao houver UID configurado, tenta descobrir via lista de usuarios do projeto Cloud.
    if not uid:
        print("[TUYA] TUYA_UID nao configurado. Tentando descobrir contas vinculadas ao projeto...")
        try:
            resp = api.get("/v1.0/apps/{schema}/users".replace("{schema}", "tuyaSmart"))
            print(f"[TUYA] Resposta /v1.0/apps/tuyaSmart/users: {resp}")
        except Exception as e:
            print(f"[TUYA] Nao foi possivel listar usuarios do app: {e}")
            print(
                "[TUYA] Dica: pegue o UID em iot.tuya.com -> seu projeto Cloud -> Devices -> "
                "Link Tuya App Account (App Accounts vinculados ao projeto)."
            )

    if uid and not home_id:
        print(f"[TUYA] TUYA_UID={uid} configurado, mas TUYA_HOME_ID ausente. Buscando homes do usuario...")
        try:
            resp = api.get(f"/v1.0/users/{uid}/homes")
            print(f"[TUYA] Resposta /v1.0/users/{uid}/homes: {resp}")
            homes = resp.get("result") or []
            for home in homes:
                print(f"  - home_id={home.get('home_id')} | name={home.get('name')}")
        except Exception as e:
            print(f"[TUYA] Falha ao buscar homes: {e}")

    # Tenta listar dispositivos por UID (mais comum para contas de app vinculadas).
    if uid:
        print(f"[TUYA] Listando dispositivos via /v1.0/users/{uid}/devices ...")
        try:
            resp = api.get(f"/v1.0/users/{uid}/devices")
            if resp.get("success"):
                _print_devices(resp.get("result") or [])
            else:
                print(f"[TUYA] Resposta sem sucesso: {resp}")
        except Exception as e:
            print(f"[TUYA] Falha ao listar dispositivos por UID: {e}")

    # Tenta listar dispositivos por HOME_ID (Smart Home API).
    if home_id:
        print(f"[TUYA] Listando dispositivos via /v1.0/homes/{home_id}/devices ...")
        try:
            resp = api.get(f"/v1.0/homes/{home_id}/devices")
            if resp.get("success"):
                _print_devices(resp.get("result") or [])
            else:
                print(f"[TUYA] Resposta sem sucesso: {resp}")
        except Exception as e:
            print(f"[TUYA] Falha ao listar dispositivos por HOME_ID: {e}")

    if not uid and not home_id:
        print(
            "[TUYA] Nem TUYA_UID nem TUYA_HOME_ID estao configurados. "
            "A conexao com a Tuya OpenAPI foi validada (autenticacao OK), "
            "mas a listagem de dispositivos requer um desses valores."
        )


if __name__ == "__main__":
    main()
