# menu.py
from dispositivos import Lampada, SensorPortao, ControleIRRF
from config_tuya import openapi

# IDs do JSON
ID_LAMPADA = "eb20e4ad6247150831lufg"
ID_SENSOR = "eba6dbc576c6cb89d0ndap"
ID_PORTAO = "eb524289f7caf9fa4duzqj"
ID_CONTROLE = "eb89c1c33a3521c211w6hn"

# Instâncias
lampada = Lampada("Luz", ID_LAMPADA, openapi)
sensor = SensorPortao("Sensor Portão", ID_SENSOR, openapi)

controle = ControleIRRF("Controle Universal", ID_CONTROLE, openapi)

def menu_lampada():
    while True:
        print("\n=== MENU LÂMPADA ===")
        print("1 - Ligar")
        print("2 - Desligar")
        print("3 - Ajustar brilho")
        print("4 - Ajustar temperatura")
        print("5 - Ver status")
        print("0 - Voltar")
        op = input("Escolha: ")
        if op == "1": lampada.ligar()
        elif op == "2": lampada.desligar()
        elif op == "3": lampada.ajustar_brilho(int(input("Brilho (10-1000): ")))
        elif op == "4": lampada.ajustar_temperatura(int(input("Temp (0-1000): ")))
        elif op == "5": lampada.status()
        elif op == "0": break

def menu_sensor():
    while True:
        print("\n=== MENU SENSOR PORTÃO ===")
        print("1 - Ver status")
        print("0 - Voltar")
        op = input("Escolha: ")
        if op == "1": sensor.status()
        elif op == "0": break


def menu_controle():
    while True:
        print("\n=== MENU CONTROLE IR/RF ===")
        print("1 - Enviar comando IR")
        print("0 - Voltar")
        op = input("Escolha: ")
        if op == "1":
            codigo = input("Digite código HEX: ")
            controle.enviar_comando_ir(codigo)
        elif op == "0": break

def menu_principal():
    while True:
        print("\n=== MENU PRINCIPAL ===")
        print("1 - Lâmpada")
        print("2 - Sensor Portão")
        print("3 - Portão Garagem")
        print("4 - Controle IR/RF")
        print("0 - Sair")
        op = input("Escolha: ")
        if op == "1": menu_lampada()
        elif op == "2": menu_sensor()
        elif op == "4": menu_controle()
        elif op == "0": break

if __name__ == "__main__":
    menu_principal()
