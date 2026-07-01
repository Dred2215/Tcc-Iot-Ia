import sys
import os
import asyncio

from ..core.config_tuya import get_home_id, get_openapi


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Defina a variável de ambiente {key} para executar os testes.")
    return value


home_id = get_home_id()
openapi = get_openapi()

LAMPADA_DEVICE_ID = _require_env("TUYA_LAMPADA_DEVICE_ID")
SENSOR_PORTAO_DEVICE_ID = _require_env("TUYA_SENSOR_PORTAO_DEVICE_ID")
PORTAO_SCENE_ID = _require_env("TUYA_PORTAO_SCENE_ID")

# ======================================================
# 📘 ENDPOINTS DE REFERÊNCIA (documentação)
# ======================================================
ENDPOINTS = {
    "device_specifications": "GET:/v1.0/iot-03/devices/{device_id}/specification",
    "device_functions": "GET:/v1.0/iot-03/devices/{device_id}/functions",
    "category_functions": "GET:/v1.0/iot-03/categories/{category}/functions",
    "send_commands": "POST:/v1.0/iot-03/devices/{device_id}/commands",
    "category_list": "GET:/v1.0/iot-03/device-categories",
    "device_status": "GET:/v1.0/iot-03/devices/{device_id}/status",
    "multiple_status": "GET:/v1.0/iot-03/devices/status",
    "status_set": "GET:/v1.0/iot-03/categories/{category}/status"
}

# ======================================================
# 🧱 CLASSE BASE
# ======================================================
class DispositivoBase:
    def __init__(self, nome, device_id, openapi):
        self.nome = nome
        self.device_id = device_id
        self.openapi = openapi
        print(f"✅ Dispositivo '{self.nome}' (ID: {self.device_id}) inicializado.")

    def _executar(self, code, value):
        """Envia comando genérico para o dispositivo"""
        commands = {"commands": [{"code": code, "value": value}]}
        self.openapi.post(f"/v1.0/iot-03/devices/{self.device_id}/commands", commands)

    def status(self):
        """Obtém status do dispositivo"""
        # 🔹 Nova verificação de conectividade real (linha adicionada)
        info = self.openapi.get(f"/v1.0/iot-03/devices/{self.device_id}")
        online = info["result"].get("online", False)
        print(f"🌐 Conectividade: {'✅ Online' if online else '❌ Offline'}")

        # 🔹 Mantém o código original
        res = self.openapi.get(f"/v1.0/iot-03/devices/{self.device_id}/status")
        print(f"📄 Status de {self.nome}:")
        for item in res.get("result", []):
            print(f" - {item['code']}: {item['value']}")
        return res


# ======================================================
# 💡 Lâmpada
# ======================================================
class Lampada(DispositivoBase):
    def ligar(self):
        self._executar("switch_led", True)
        print("💡 Lâmpada ligada.")

    def desligar(self):
        self._executar("switch_led", False)
        print("💡 Lâmpada desligada.")

# ======================================================
# 🚪 Sensor de Portão
# ======================================================
class SensorPortao(DispositivoBase):
    def estado_portao(self):
        """Retorna o estado atual do portão"""
        try:
            res = self.openapi.get(f"/v1.0/iot-03/devices/{self.device_id}/status")
            for item in res.get("result", []):
                if item["code"] == "doorcontact_state":
                    estado = item["value"]
                    status_texto = "🚪 Aberto" if estado else "🔒 Fechado"
                    print(f"{self.nome}: {status_texto}")
                    return estado
            print(f"⚠️ Código 'doorcontact_state' não encontrado para {self.nome}.")
        except Exception as e:
            print(f"❌ Erro ao obter estado do portão: {e}")

# ======================================================
# 🧩 Cena (Portão Garagem)
# ======================================================
class Portao:
    def __init__(self, nome, openapi, home_id, scene_id):
        self.nome = nome
        self.openapi = openapi
        self.home_id = home_id
        self.scene_id = scene_id
        print(f"✅ Cena '{self.nome}' (SceneID: {self.scene_id}) inicializada.")

    def acionar(self):
        print(f"🚪 Executando cena '{self.nome}'...")

        path = f"/v1.0/homes/{self.home_id}/scenes/{self.scene_id}/trigger"

        try:
            # Tentativa 1: corpo nulo (funciona na maioria dos casos)
            res = self.openapi.post(path, None)
            if res.get("success"):
                print(f"✅ Cena '{self.nome}' executada com sucesso!")
                return

            # Tentativa 2: corpo vazio {} (fallback)
            if res.get("code") == 1004:
                print("⚠️  Erro 1004 (sign invalid). Tentando novamente com body={} ...")
                res2 = self.openapi.post(path, {})
                if res2.get("success"):
                    print(f"✅ Cena '{self.nome}' executada com sucesso (fallback)!")
                    return
                else:
                    print(f"❌ Falha ao acionar cena (fallback): {res2}")
                    return

            # Outro erro
            print(f"❌ Falha ao acionar '{self.nome}': {res}")

        except Exception as e:
            print(f"⚠️  Erro ao tentar acionar cena: {e}")


# ======================================================
# ⚙️ REGISTRO DE DISPOSITIVOS
# ======================================================
DISPOSITIVOS = {
    "lampada": Lampada("Luz", LAMPADA_DEVICE_ID, openapi),
    "sensor_portao": SensorPortao("Sensor Portão", SENSOR_PORTAO_DEVICE_ID, openapi)
}

CENAS = {
    "portao": Portao("Portão Garagem", openapi, home_id, PORTAO_SCENE_ID)
}

# ======================================================
# 🔍 FERRAMENTAS DE TESTE INTERATIVO
# ======================================================
def listar_dispositivos():
    print("\n📋 Dispositivos disponíveis:")
    for idx, nome in enumerate(DISPOSITIVOS.keys(), start=1):
        print(f"  {idx}. {nome}")
    for idx, nome in enumerate(CENAS.keys(), start=len(DISPOSITIVOS)+1):
        print(f"  {idx}. {nome} (Cena)")
    print()

def selecionar_dispositivo():
    listar_dispositivos()
    escolha = input("🔢 Escolha o número do dispositivo que deseja testar: ").strip()
    try:
        escolha = int(escolha)
        if 1 <= escolha <= len(DISPOSITIVOS):
            nome = list(DISPOSITIVOS.keys())[escolha - 1]
            return DISPOSITIVOS[nome]
        elif len(DISPOSITIVOS) < escolha <= len(DISPOSITIVOS) + len(CENAS):
            nome = list(CENAS.keys())[escolha - len(DISPOSITIVOS) - 1]
            return CENAS[nome]
        else:
            print("❌ Número inválido.")
            return None
    except ValueError:
        print("❌ Entrada inválida. Digite um número.")
        return None

async def testar_dispositivo(dispositivo):
    print(f"\n🚀 Testando dispositivo: {dispositivo.nome}")

    if isinstance(dispositivo, Lampada):
        print("💡 Ligando a lâmpada...")
        dispositivo.ligar()
        await asyncio.sleep(2)
        print("💡 Desligando a lâmpada...")
        dispositivo.desligar()
        await asyncio.sleep(1)
        dispositivo.status()

    elif isinstance(dispositivo, Portao):
        print("🚪 Acionando cena do portão...")
        dispositivo.acionar()

    elif isinstance(dispositivo, SensorPortao):
        print("🔍 Verificando estado do portão...")
        dispositivo.estado_portao()

    else:
        print("⚠️ Tipo de dispositivo não reconhecido.")

# ======================================================
# 🧾 LISTAR DISPOSITIVOS E CENAS COM ID
# ======================================================
def listar_dispositivos_e_cenas(openapi, home_id):
    print("\n📡 Buscando dispositivos e cenas na sua conta Tuya Cloud...")

    # --- Lista de dispositivos ---
    try:
        dispositivos_data = openapi.get(f"/v1.0/homes/{home_id}/devices")
        if dispositivos_data.get("success"):
            dispositivos = dispositivos_data.get("result", [])
            print("\n💡 Dispositivos encontrados:")
            for i, disp in enumerate(dispositivos, start=1):
                nome = disp.get("name", "Sem nome")
                dev_id = disp.get("id", "Desconhecido")
                print(f"  {i}. {nome} (Device ID: {dev_id})")
            print(f"✅ Total de dispositivos: {len(dispositivos)}")
        else:
            print(f"❌ Falha ao buscar dispositivos: {dispositivos_data}")
    except Exception as e:
        print(f"⚠️ Erro ao buscar dispositivos: {e}")

    # --- Lista de cenas ---
    try:
        cenas_data = openapi.get(f"/v1.0/homes/{home_id}/scenes")
        if cenas_data.get("success"):
            cenas = cenas_data.get("result", [])
            print("\n🎬 Cenas disponíveis:")
            for i, cena in enumerate(cenas, start=1):
                nome = cena.get("name", "Sem nome")
                scene_id = cena.get("scene_id", "Desconhecido")
                print(f"  {i}. 🎞️ {nome} (Scene ID: {scene_id})")
            print(f"✅ Total de cenas: {len(cenas)}")
        else:
            print(f"❌ Falha ao buscar cenas: {cenas_data}")
    except Exception as e:
        print(f"⚠️ Erro ao buscar cenas: {e}")

    print("\n📋 Fim da listagem geral.\n")


# ======================================================
# 🧠 EXECUÇÃO PRINCIPAL
# ======================================================
async def main():
    print("🔧 ECHO TEST – Diagnóstico de dispositivos Tuya Cloud")
    print("📘 Endpoints disponíveis:")
    for nome, url in ENDPOINTS.items():
        print(f"  - {nome}: {url}")
    print()

    # 🆕 Mostrar todos os dispositivos e cenas logo no início
    listar_dispositivos_e_cenas(openapi, home_id)
    print()

    while True:
        disp = selecionar_dispositivo()
        if disp:
            await testar_dispositivo(disp)
        again = input("\nDeseja testar outro dispositivo? (s/n): ").strip().lower()
        if again != "s":
            break

    print("\n👋 Encerrando teste de dispositivos.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Teste interrompido pelo usuário.")
        sys.exit(0)
