import requests
import asyncio
import time
from backend.src.tratamento_response_IA import processar_resposta

# URL do webhook
WEBHOOK_URL = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook/test-message"

# Variável global para armazenar a última resposta da IA
respostaIA = None  

def enviar_comando():
    global respostaIA  

    while True:
        comando = input("Digite o comando (ou 'sair' para encerrar): ").strip()
        
        if comando.lower() == "sair":
            print("Encerrando...")
            break
        
        if not comando:
            print("Comando vazio, tente novamente.")
            continue

        try:
            # Envia o comando para o webhook
            response = requests.post(WEBHOOK_URL, json={"comando": comando})
            response.raise_for_status()

            # Guarda a resposta na variável global
            respostaIA = response.json()
            print("Resposta da IA recebida:", respostaIA)

            # Marca o tempo inicial
            inicio = time.perf_counter()

            # Executa assincronamente
            asyncio.run(processar_resposta(respostaIA))

            # Marca o tempo final
            fim = time.perf_counter()
            duracao = fim - inicio
            print(f"\n⏱️ Tempo total de execução: {duracao:.2f} segundos\n")

        except requests.exceptions.RequestException as e:
            print("Erro na requisição:", e)

if __name__ == "__main__":
    enviar_comando()
