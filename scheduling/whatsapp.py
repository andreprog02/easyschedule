import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

def limpar_telefone(telefone):
    """Garante formato 5511999999999"""
    numeros = re.sub(r'\D', '', telefone)
    if len(numeros) <= 11:
        numeros = f"55{numeros}"
    return numeros

def enviar_mensagem_evolution(cliente_nome, cliente_telefone, data, hora, servico, profissional, tipo='confirmacao'):
    """
    Envia mensagem via Evolution API (v1 ou v2).
    tipo: 'confirmacao' ou 'cancelamento'
    """
    # 1. Carrega configurações do .env
    api_url = os.getenv("EVOLUTION_API_URL")
    api_key = os.getenv("AUTHENTICATION_API_KEY")
    nome_instancia = os.getenv("EVOLUTION_INSTANCE_NAME")

    if not api_url or not api_key:
        print("❌ Evolution API não configurada no .env")
        return False

    # 2. Monta a Mensagem
    telefone_formatado = limpar_telefone(cliente_telefone)
    
    if tipo == 'cancelamento':
        texto = (
            f"🚫 *Cancelamento de Agendamento*\n\n"
            f"Olá, {cliente_nome}. Infelizmente seu horário de *{servico}* "
            f"no dia *{data}* às *{hora}* precisou ser cancelado.\n\n"
            f"Por favor, entre em contato para reagendar."
        )
    else:
        texto = (
            f"✅ *Confirmação de Agendamento*\n\n"
            f"Olá, *{cliente_nome}*! Tudo confirmado.\n\n"
            f"🗓 *Data:* {data}\n"
            f"⏰ *Horário:* {hora}\n"
            f"✂ *Serviço:* {servico}\n"
            f"👤 *Profissional:* {profissional}\n\n"
            f"Te esperamos lá!"
        )

    # 3. Prepara envio
    url = f"{api_url}/message/sendText/{nome_instancia}"
    
    payload = {
        "number": telefone_formatado,
        "options": {"delay": 1000, "presence": "composing"},
        "textMessage": {"text": texto}
    }
    
    headers = {
        "apikey": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Evolution API: {response.status_code} - {response.text}")
        return response.status_code == 201 or response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar WhatsApp: {e}")
        return False