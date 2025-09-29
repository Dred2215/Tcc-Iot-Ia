import requests

# URL do webhook
url = "https://nery-automa-n8n.dlivfa.easypanel.host/webhook-test/response_ia_redis"

# Fazendo a requisição GET
try:
    resposta = requests.get(url)
    
    # Verifica se a requisição foi bem-sucedida
    if resposta.status_code == 200:
        print("Resposta recebida com sucesso:")
        print(resposta.text)  # ou resposta.json() se for um JSON
    else:
        print(f"Erro na requisição: {resposta.status_code}")
        print(resposta.text)

except Exception as e:
    print(f"Ocorreu um erro: {e}")