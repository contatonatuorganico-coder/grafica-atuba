import base64
import os
import requests
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# Variáveis de Ambiente
EVOLUTION_URL = os.environ.get("EVOLUTION_API_URL", "https://evolution-api-production-5008.up.railway.app").rstrip("/")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE_NAME", "grafica-atuba")
API_KEY = os.environ.get("EVOLUTION_API_KEY", "5F1D6E603161-4C5D-9DBA-7A59564694BF")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    # Configura a SDK oficial do Google com a chave (formato AQ ou AIza)
    genai.configure(api_key=GEMINI_API_KEY)

def processar_resposta(mensagem_cliente, imagem_bytes=None, mime_type=None):
    if not GEMINI_API_KEY:
        print(">>> AVISO: GEMINI_API_KEY não foi configurada nas Variáveis de Ambiente!", flush=True)
        return (
            "Olá! Seja bem-vindo à *Gráfica Atuba*! 🖨️✨\n\n"
            "Recebemos sua mensagem. Como podemos ajudar com seus materiais impressos hoje?"
        )

    prompt_sistema = """
    Você é o assistente virtual comercial da **Gráfica Atuba**.
    Seu objetivo é atender os clientes no WhatsApp, tirar dúvidas, analisar fotos enviadas e fornecer orçamentos com base na nossa tabela de preços.

    TABELA DE PREÇOS DE REFERÊNCIA (Valores aproximados para orçamento inicial):
    1. Cartão de Visita (Couché 300g, 9x5cm, Verniz UV):
       - 500 unidades: R$ 95,00
       - 1.000 unidades: R$ 140,00
    2. Panfletos / Flyings (Couché 115g, 10x14cm, 4x0 cores):
       - 1.000 unidades: R$ 180,00
       - 2.500 unidades: R$ 260,00
       - 5.000 unidades: R$ 390,00
    3. Banners em Lona 440g (com acabamento em bastão, ponteira e cordão):
       - Tam. 0,60 x 0,90m: R$ 75,00
       - Tam. 0,70 x 1,00m: R$ 95,00
       - Tam. 1,00 x 1,50m: R$ 160,00
    4. Adesivos Personalizados (Vinil Brilho ou Fosco com corte especial):
       - 100 unidades (5x5cm): R$ 65,00
       - 500 unidades (5x5cm): R$ 150,00
    5. Block de Pedidos / Talões (2 vias autocopiativas, 50 jogos cada):
       - 5 talões A5: R$ 130,00
       - 10 talões A5: R$ 210,00

    INSTRUÇÕES DE RESPOSTA:
    - Se o cliente enviar uma **imagem/foto**, analise a imagem e identifique o tipo de material gráfico visível.
    - Dê preços diretos usando a tabela acima quando o cliente perguntar por um produto específico.
    - Se o cliente pedir uma quantidade ou formato diferente, ofereça a estimativa aproximada e informe que a equipe comercial ajusta para medidas personalizadas.
    - Seja cortês, profissional, use emojis com moderação e convide o cliente a enviar a arte final ou tirar dúvidas.
    """

    try:
        # Chama via SDK oficial do Google Generative AI
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        conteudos = [
            {"role": "user", "parts": [prompt_sistema, f"Mensagem do cliente: {mensagem_cliente}"]}
        ]

        if imagem_bytes and mime_type:
            conteudos[0]["parts"].append({
                "mime_type": mime_type,
                "data": imagem_bytes
            })

        response = model.generate_content(conteudos)
        if response and response.text:
            return response.text
    except Exception as e:
        print(f">>> ERRO EXATO NA CHAMADA GEMINI: {e}", flush=True)

    return (
        "Olá! Seja bem-vindo à *Gráfica Atuba*! 🖨️✨\n\n"
        "Recebemos o seu contato. Como podemos ajudar com seus materiais impressos hoje?"
    )

@app.route("/", methods=["GET"])
def home():
    return "Grafica Atuba - Atendimento IA Ativo!"

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

        if data.get("fromMe", False) or sub_data.get("key", {}).get("fromMe", False):
            return "OK", 200

        key_data = sub_data.get("key", {}) if isinstance(sub_data, dict) else {}
        remote_jid = key_data.get("remoteJid", "") or data.get("remoteJid", "")

        if not remote_jid or "status" in str(data.get("event", "")).lower():
            return "OK", 200

        message_obj = sub_data.get("message", {}) if isinstance(sub_data, dict) and "message" in sub_data else data
        if isinstance(message_obj, list) and len(message_obj) > 0:
            message_obj = message_obj[0] if isinstance(message_obj[0], dict) else {}

        user_message = ""
        imagem_bytes = None
        mime_type = None

        if isinstance(message_obj, dict):
            if "conversation" in message_obj:
                user_message = message_obj["conversation"]
            elif "extendedTextMessage" in message_obj and isinstance(message_obj["extendedTextMessage"], dict):
                user_message = message_obj["extendedTextMessage"].get("text", "")
            elif "imageMessage" in message_obj and isinstance(message_obj["imageMessage"], dict):
                img_data = message_obj["imageMessage"]
                user_message = img_data.get("caption", "Foto enviada para orçamento de impressão")
                if "base64" in img_data:
                    try:
                        imagem_bytes = base64.b64decode(img_data["base64"])
                        mime_type = img_data.get("mimetype", "image/jpeg")
                    except Exception:
                        pass

        if not user_message and isinstance(data, dict):
            if "text" in data:
                if isinstance(data["text"], dict):
                    user_message = data["text"].get("message", "")
                elif isinstance(data["text"], str):
                    user_message = data["text"]
            elif "body" in data:
                user_message = str(data.get("body", ""))

        if not user_message and not imagem_bytes:
            user_message = "Olá!"

        resposta_bot = processar_resposta(user_message, imagem_bytes=imagem_bytes, mime_type=mime_type)

        url_envio = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
        headers = {
            "apikey": API_KEY,
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        payload_envio = {
            "number": str(remote_jid),
            "text": resposta_bot
        }

        try:
            resp_envio = requests.post(url_envio, json=payload_envio, headers=headers, timeout=10)
            if resp_envio.status_code not in [200, 201]:
                numero_limpo = "".join(filter(str.isdigit, str(remote_jid)))
                requests.post(url_envio, json={"number": numero_limpo, "text": resposta_bot}, headers=headers, timeout=10)
        except Exception as err_envio:
            print(f"Erro no envio da resposta: {err_envio}", flush=True)

        return "OK", 200
    except Exception as e:
        print(f"Erro no webhook: {e}", flush=True)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

