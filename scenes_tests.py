# scene_tests.py
from config_tuya import openapi, UID

def listar_homes(uid: str):
    """Retorna a lista de homes do usuário (UID)."""
    try:
        resp = openapi.get(f"/v1.0/users/{uid}/homes")
        if resp.get("success"):
            homes = resp.get("result", [])
            print(f"✅ Homes do UID {uid}: {len(homes)}")
            for h in homes:
                print(f"- home_id={h.get('home_id')} | nome={h.get('name')}")
            return homes
        print("❌ Erro ao listar homes:", resp)
    except Exception as e:
        print("⚠️ Erro na requisição de homes:", e)
    return []

def listar_cenas(home_id: str, version="v1.0"):
    """Retorna a lista de cenas (Tap-to-Run) do home."""
    path = f"/{version}/homes/{home_id}/scenes"
    try:
        resp = openapi.get(path)
        if resp.get("success"):
            cenas = resp.get("result", [])
            print(f"\n✅ Cenas no home {home_id}: {len(cenas)}")
            for c in cenas:
                print(f"- scene_id={c.get('scene_id')} | name={c.get('name')}")
            return cenas
        print(f"❌ Erro ao listar cenas do home {home_id}:", resp)
    except Exception as e:
        print(f"⚠️ Erro na requisição de cenas do home {home_id}:", e)
    return []

def acionar_cena(home_id: str, scene_id: str):
    """Aciona (trigger) uma cena do home, tentando assinatura com body None e fallback {}."""
    path = f"/v1.0/homes/{home_id}/scenes/{scene_id}/trigger"

    try:
        # Tentativa 1: sem corpo (None)
        resp = openapi.post(path, None)
        if resp.get("success"):
            print(f"✅ Cena acionada com sucesso! home_id={home_id} scene_id={scene_id}")
            return True

        # Se falhou com 1004, tenta novamente com corpo {}
        code = resp.get("code")
        if code == 1004:
            print("ℹ️ Tentativa com body=None retornou 1004. Repetindo com body={}.")
            resp2 = openapi.post(path, {})
            if resp2.get("success"):
                print(f"✅ Cena acionada com sucesso (fallback)! home_id={home_id} scene_id={scene_id}")
                return True
            else:
                print(f"❌ Falha ao acionar cena (fallback): {resp2}")
                return False

        # Outros erros
        print(f"❌ Falha ao acionar cena: {resp}")
        return False

    except Exception as e:
        print(f"⚠️ Erro ao acionar cena: {e}")
        return False


def confirmar(msg: str) -> bool:
    """Confirmação simples via input()."""
    ans = input(f"{msg} (s/n): ").strip().lower()
    return ans in ("s", "sim", "y", "yes")

def escolher_home(homes: list) -> dict | None:
    if not homes:
        return None
    if len(homes) == 1:
        return homes[0]
    print("\nSelecione o home pelo índice:")
    for i, h in enumerate(homes, start=1):
        print(f"{i}) {h.get('name')} [{h.get('home_id')}]")
    while True:
        sel = input("Índice do home: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(homes):
            return homes[int(sel) - 1]
        print("Índice inválido.")

def escolher_cena(cenas: list) -> dict | None:
    if not cenas:
        return None
    if len(cenas) == 1:
        return cenas[0]
    print("\nSelecione a cena pelo índice:")
    for i, c in enumerate(cenas, start=1):
        print(f"{i}) {c.get('name')} [{c.get('scene_id')}]")
    while True:
        sel = input("Índice da cena: ").strip()
        if sel.isdigit() and 1 <= int(sel) <= len(cenas):
            return cenas[int(sel) - 1]
        print("Índice inválido.")

if __name__ == "__main__":
    # 1) listar homes
    homes = listar_homes(UID)
    if not homes:
        raise SystemExit(1)

    # 2) escolher home
    home = escolher_home(homes)
    if not home:
        print("Nenhum home selecionado.")
        raise SystemExit(1)

    home_id = str(home.get("home_id"))

    # 3) listar cenas do home
    cenas = listar_cenas(home_id, version="v1.0")
    if not cenas:
        print("Nenhuma cena encontrada para este home.")
        raise SystemExit(0)

    # 4) escolher cena
    cena = escolher_cena(cenas)
    if not cena:
        print("Nenhuma cena selecionada.")
        raise SystemExit(1)

    scene_id = str(cena.get("scene_id"))
    scene_name = cena.get("name")

    # 5) confirmação
    if confirmar(f"\nConfirmar acionamento da cena '{scene_name}' (scene_id={scene_id}) no home {home_id}?"):
        acionar_cena(home_id, scene_id)
    else:
        print("❎ Ação cancelada pelo usuário.")
