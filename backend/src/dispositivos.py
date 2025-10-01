
# dispositivos_base.py
from src.config_tuya import openapi

class DispositivoBase:
    def __init__(self, nome, device_id, openapi):
        self.nome = nome
        self.device_id = device_id
        self.openapi = openapi
        print(f"✅ Dispositivo '{self.nome}' (ID: {self.device_id}) inicializado.")

    def _executar(self, code, value):
        """Envia comando genérico para o dispositivo"""
        commands = {"commands": [{"code": code, "value": value}]}
        openapi.post(f'/v1.0/iot-03/devices/{self.device_id}/commands', commands)

    def status(self):
        """Obtém status do dispositivo"""
        res = openapi.get(f'/v1.0/iot-03/devices/{self.device_id}/status')
        print(f"📄 Status de {self.nome}:")
        for item in res.get("result", []):
            print(f"{item['code']}: {item['value']}")



class CenaBase:
    """
    Classe base para qualquer 'dispositivo' que é, na verdade,
    controlado pela ativação de uma cena (Tap-to-Run) na Tuya.
    """
    def __init__(self, nome: str, openapi, home_id: str, scene_id: str):
        self.nome = nome
        self.openapi = openapi
        self.home_id = home_id
        self.scene_id = scene_id
        print(f"✅ Dispositivo de cena '{self.nome}' (ID: {self.scene_id}) inicializado.")

    def _acionar_cena(self) -> bool:
        """
        Lógica central e protegida para acionar (trigger) a cena.
        Este método contém a comunicação com a API, incluindo o fallback.
        """
        path = f"/v1.0/homes/{self.home_id}/scenes/{self.scene_id}/trigger"
        try:
            # Tentativa 1: com corpo nulo (funciona na maioria das vezes)
            resp = self.openapi.post(path, None)
            if resp.get("success"):
                print(f"✅ Cena '{self.nome}' acionada com sucesso.")
                return True

            # Tentativa 2 (fallback): se o erro for de assinatura, tenta com corpo vazio
            if resp.get("code") == 1004:
                print(f"ℹ️  Falha de assinatura (1004). Tentando com body={{}} como fallback.")
                resp2 = self.openapi.post(path, {})
                if resp2.get("success"):
                    print(f"✅ Cena '{self.nome}' acionada com sucesso (fallback).")
                    return True
                else:
                    print(f"❌ Falha ao acionar cena (fallback): {resp2}")
                    return False

            # Lida com outros erros
            print(f"❌ Falha ao acionar cena: {resp}")
            return False
        except Exception as e:
            print(f"⚠️  Erro na requisição para acionar a cena: {e}")
            return False

    def status(self):
        """Informa que o status de uma cena não é consultável diretamente."""
        print(f"ℹ️  O status de uma cena como '{self.nome}' não pode ser consultado diretamente via API.")

class Portao(CenaBase):
    """
    Representa um portão que é ativado por uma única cena (ex: um botão de controle).
    Herda toda a lógica de acionamento de CenaBase.
    """
    def __init__(self, nome: str, openapi, home_id: str, scene_id_acionar: str):
        # Passa todas as informações para o construtor da classe pai (CenaBase)
        super().__init__(nome, openapi, home_id, scene_id_acionar)

    def acionar(self):
        """
        Aciona o portão. Este método é uma interface amigável que chama
        a lógica de acionamento real implementada na classe base.
        """
        print(f"▶️  Enviando comando para acionar '{self.nome}'...")
        return self._acionar_cena()


# 💡 Lâmpada inteligente
class Lampada(DispositivoBase):
    def ligar(self): self._executar("switch_led", True)
    def desligar(self): self._executar("switch_led", False)
    def alterar_modo(self, modo): self._executar("work_mode", modo)
    def ajustar_brilho(self, valor): self._executar("bright_value_v2", valor)
    def ajustar_temperatura(self, valor): self._executar("temp_value_v2", valor)
    def definir_cor(self, h, s, v): self._executar("colour_data_v2", {"h": h, "s": s, "v": v})
    def definir_cena(self, cena_json): self._executar("scene_data_v2", cena_json)
    def definir_musica(self, musica_json): self._executar("music_data", musica_json)

# 🚪 Sensor de portão
class SensorPortao(DispositivoBase):
    def estado_portao(self):
        res = self.status()
        # Aqui poderia filtrar apenas "doorcontact_state"
        return res


# 🎮 Controle IR/RF universal
class ControleIRRF(DispositivoBase):
    def enviar_comando_ir(self, codigo_hex):
        self._executar("ir_send", codigo_hex)
    def aprender_comando_ir(self, codigo_bruto):
        self._executar("ir_study_code", codigo_bruto)
