import requests
import os
from dotenv import load_dotenv

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

# 2. Pega os valores seguros (Se não achar, retorna None)
URL_API = os.getenv("EVOLUTION_API_URL")
API_KEY = os.getenv("AUTHENTICATION_API_KEY") # Pega a chave que já estava no .env
NOME_INSTANCIA = os.getenv("EVOLUTION_INSTANCE_NAME")
SEU_TELEFONE = os.getenv("EVOLUTION_USER_PHONE")

# Verifica se carregou tudo antes de tentar enviar
if not API_KEY or not SEU_TELEFONE:
    print("❌ Erro: Variáveis de ambiente não encontradas. Verifique o arquivo .env")
    exit()

# Na v1, o endpoint é assim:
url = f"{URL_API}/message/sendText/{NOME_INSTANCIA}"

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

payload = {
    "number": SEU_TELEFONE,
    "textMessage": {
        "text": "Olá! Teste seguro usando variáveis de ambiente! 🐍🚀🔒"
    }
}

print(f"📤 Enviando para {SEU_TELEFONE}...")

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Resposta:", response.json())
except Exception as e:
    print(f"Erro: {e}")