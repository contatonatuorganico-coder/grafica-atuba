import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

# Memória temporária para números pausados
ATENDIMENTO_HUMANO = set()

# Variáveis de Ambiente
EVOLUTION_URL = os.environ.get("EVOLUTION_API_URL", "https://evolution-api-production-5008.up.railway.app").rstrip("/")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE_NAME", "grafica-atuba")
API_KEY = os.environ.get("EVOLUTION_API_KEY", "5F1D6E603161-4C5D-9DBA-7A59564694BF")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Inicializa o cliente oficial google-genai
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Mensagem Padrão de Boas-Vindas
MENSAGEM_BOAS_VINDAS = (
    "Olá! Seja bem-vindo(a) à *Gráfica Atuba*! 🖨️✨\n\n"
    "Sou o assistente virtual e posso te ajudar com orçamentos rápidos de:\n"
    "• Cartões de Visita\n"
    "• Panfletos / Flyers\n"
    "• Banners em Lona\n"
    "• Adesivos Personalizados\n"
    "• Blocos de Pedidos / Talões\n\n"
    "Como posso te ajudar hoje?\n"
    "*(Digite *#atendente* a qualquer momento para falar com nossa equipe).*"
)

def enviar_mensagem_whatsapp(numero, texto):
    """Função para envio via Evolution API"""
    url_envio = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {
        "apikey": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload_envio = {
        "number": str(numero),
        "text": texto,
        "delay": 1200
    }
    try:
        resp = requests.post(url_envio, json=payload_envio, headers=headers, timeout=15)
        if resp.status_code not in [200, 201]:
            numero_limpo = "".join(filter(str.isdigit, str(numero)))
            requests.post(url_envio, json={"number": numero_limpo, "text": texto, "delay": 1200}, headers=headers, timeout=15)
    except Exception as err:
        print(f"Erro ao enviar WhatsApp: {err}", flush=True)

def processar_resposta(mensagem_cliente):
    msg_limpa = mensagem_cliente.strip().lower()

    # Se for apenas saudação, envia boas-vindas
    saudacoes_puras = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "inicio", "início"]
    if msg_limpa in saudacoes_puras:
        return MENSAGEM_BOAS_VINDAS

    if not client:
        print(">>> ERRO: GEMINI_API_KEY não localizada!", flush=True)
        return "Olá! Nosso assistente está indisponível no momento. Um de nossos atendentes falará com você em breve!"

    prompt_sistema = """
    Você é o assistente virtual comercial da **Gráfica Atuba**.
    Sua missão é atender clientes no WhatsApp de forma natural, simpática e fluida.

    TABELA DE PREÇOS DE REFERÊNCIA:
    1. Cartão de Visita (Couché 300g, 9x5cm, Verniz UV total frente):
       - 500 unidades: R$ 95,00
       - 1.000 unidades (milheiro): R$ 140,00
    2. Panfletos / Flyers (Couché 115g, 10x14cm, colorido frente):
       - 1.000 unidades: R$ 180,00
       - 2.500 unidades: R$ 260,00
       - 5.000 unidades: R$ 390,00
    3. Banners em Lona 440g (com bastão, ponteira e cordão):
       - Tam. 0,60 x 0,90m: R$ 75,00
       - Tam. 0,70 x 1,00m: R$ 95,00
       - Tam. 1,00 x 1,50m: R$ 160,00
    4. Adesivos Personalizados (Vinil Brilho com corte especial):
       - 100 unidades (5x5cm): R$ 65,00
       - 500 unidades (5x5cm): R$ 150,00
    5. Bloco de Pedidos / Talões (2 vias autocopiativas, 50 jogos cada):
       - 5 talões A5: R$ 130,00
       - 10 talões A5: R$ 210,00

    REGRAS DE CONVERSA:
    - Seja direto e responda EXATAMENTE sobre o produto perguntado. Exemplo: se o cliente pedir "cartão de visita", envie os valores do cartão de visita.
    - Não repita o menu de boas-vindas se o cliente já especificou o produto.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt_sistema}\n\nMensagem do cliente: {mensagem_cliente}"
        )
        if response and response.text:
            return response.text
    except Exception as e:
        print(f">>> ERRO API GEMINI: {e}", flush=True)

    return "Olá! Recebemos sua mensagem. Um de nossos atendentes dará continuidade ao seu orçamento em instantes!"

@app.route("/", methods=["GET"])
def home():
    return "Gráfica Atuba - Bot Gratuito Ativo!"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_payload = request.get_json(silent=True)
        if not raw_payload:
            return "OK", 200

        data = raw_payload[0] if isinstance(raw_payload, list) and len(raw_payload) > 0 else raw_payload
        if not isinstance(data, dict):
            return "OK", 200

        sub_data = data.get("data", {})
        if isinstance(sub_data, list) and len(sub_data) > 0:
            sub_data = sub_data[0] if isinstance(sub_data[0], dict) else {}
        if not isinstance(sub_data, dict):
            sub_data = {}

        key_data = sub_data.get("key", {}) if isinstance(sub_data, dict) else {}
        remote_jid = key_data.get("remoteJid", "") or data.get("remoteJid", "")

        if not remote_jid or "status" in str(data.get("event", "")).lower():
            return "OK", 200

        is_from_me = data.get("fromMe", False) or key_data.get("fromMe", False)

        message_obj = sub_data.get("message", {}) if isinstance(sub_data, dict) and "message" in sub_data else data
        if isinstance(message_obj, list) and len(message_obj) > 0:
            message_obj = message_obj[0] if isinstance(message_obj[0], dict) else {}

        user_message = ""
        if isinstance(message_obj, dict):
            if "conversation" in message_obj:
                user_message = message_obj["conversation"]
            elif "extendedTextMessage" in message_obj and isinstance(message_obj["extendedTextMessage"], dict):
                user_message = message_obj["extendedTextMessage"].get("text", "")

        if not user_message and isinstance(data, dict):
            if "text" in data:
                if isinstance(data["text"], dict):
                    user_message = data["text"].get("message", "")
                elif isinstance(data["text"], str):
                    user_message = data["text"]
            elif "body" in data:
                user_message = str(data.get("body", ""))

        msg_clean = user_message.strip().lower()

        gatilhos_pausa = ["#pausa", "#atendente", "#humano", "#pausar"]
        gatilhos_retorno = ["#voltar", "#ia", "#bot", "#ativar"]

        if msg_clean in gatilhos_pausa:
            ATENDIMENTO_HUMANO.add(remote_jid)
            enviar_mensagem_whatsapp(remote_jid, "⏸️ *Atendimento automático pausado.* Um de nossos atendentes continuará por aqui!")
            return "OK", 200

        if msg_clean in gatilhos_retorno:
            ATENDIMENTO_HUMANO.discard(remote_jid)
            enviar_mensagem_whatsapp(remote_jid, "🤖 *Atendimento automático reativado!* Como posso te ajudar?")
            return "OK", 200

        if is_from_me:
            return "OK", 200

        if remote_jid in ATENDIMENTO_HUMANO:
            return "OK", 200

        if not user_message:
            return "OK", 200

        resposta_bot = processar_resposta(user_message)
        enviar_mensagem_whatsapp(remote_jid, resposta_bot)

        return "OK", 200
    except Exception as e:
        print(f"Erro no webhook: {e}", flush=True)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
