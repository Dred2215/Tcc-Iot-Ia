import sys
import asyncio
from tuya_connector import TuyaOpenAPI

# ======================================================
# 🔐 CONFIGURAÇÃO TUYA CLOUD
# ======================================================
ACCESS_ID = "4jgyc5ex3wagcdt5eycs"
ACCESS_SECRET = "fc51f69c94704a548ebb5537809ea9a0"
ENDPOINT = "https://openapi.tuyaus.com"
UID = "az1636816675981dWC2h"
home_id = "54688414"

print("🌐 Conectando à API Tuya Cloud...")
openapi = TuyaOpenAPI(ENDPOINT, ACCESS_ID, ACCESS_SECRET)
openapi.connect()
print("✅ Conexão estabelecida com sucesso.\n")

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
        res = self.openapi.post(f"/v1.0/homes/{self.home_id}/scenes/{self.scene_id}/trigger", {})
        if res.get("success"):
            print(f"✅ Cena '{self.nome}' executada com sucesso!")
        else:
            print(f"❌ Falha ao acionar '{self.nome}': {res}")

# ======================================================
# ⚙️ REGISTRO DE DISPOSITIVOS
# ======================================================
DISPOSITIVOS = {
    "lampada": Lampada("Luz", "eb20e4ad6247150831lufg", openapi),
    "sensor_portao": SensorPortao("Sensor Portão", "eba6dbc576c6cb89d0ndap", openapi)
}

CENAS = {
    "portao": Portao("Portão Garagem", openapi, home_id, "yp6IXiAOst5s66wX")
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
# 🧠 EXECUÇÃO PRINCIPAL
# ======================================================
async def main():
    print("🔧 ECHO TEST – Diagnóstico de dispositivos Tuya Cloud")
    print("📘 Endpoints disponíveis:")
    for nome, url in ENDPOINTS.items():
        print(f"  - {nome}: {url}")
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
