import os
import requests


WEBHOOK_URL = os.getenv("N8N_REDIS_TEST_WEBHOOK")


def fetch_cache_snapshot() -> None:
    if not WEBHOOK_URL:
        raise RuntimeError("Defina a variável de ambiente N8N_REDIS_TEST_WEBHOOK para usar este utilitário.")

    try:
        resposta = requests.get(WEBHOOK_URL)
        if resposta.status_code == 200:
            print("Resposta recebida com sucesso:")
            print(resposta.text)  # ou resposta.json() se for um JSON
        else:
            print(f"Erro na requisição: {resposta.status_code}")
            print(resposta.text)
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


if __name__ == "__main__":
    fetch_cache_snapshot()
