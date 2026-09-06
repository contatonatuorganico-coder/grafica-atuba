import base64
import os
import requests
from flask import Flask, request

app = Flask(__name__)

EVOLUTION_URL = os.environ.get("EVOLUTION_URL", "https://evolution-api-production-5008.up.railway.app").rstrip("/")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "atendimento")
API_KEY = os.environ.get("API_KEY", "97d3f3aee5196398da165c49b3a5a8fe2d28507ac3742c356fe88c897fec9bcc")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def processar_resposta(mensagem_cliente, imagem_bytes=None, mime_type=None):
    if mensagem_cliente and not imagem_bytes:
        mensagem_limpa = mensagem_cliente.strip().lower()
        if any(s in mensagem_limpa for s in ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "eae", "salve", "hey"]) and len(mensagem_limpa) < 30:
            return (
                "Olá! Seja bem-vindo à *Gráfica Atuba*! 🖨️✨\n\n"
                "Mande aqui a foto do seu material gráfico ou descreva o que você precisa (cartões de visita, panfletos, banners, adesivos) para realizarmos o seu atendimento e orçamento!"
            )

    if not GEMINI_API_KEY:
        return (
            "Olá! Seja bem-vindo à *Gráfica Atuba*! 🖨️✨\n\n"
            "Recebemos sua mensagem. Como podemos ajudar com seus materiais impressos hoje?"
        )

    prompt_texto = f"""
    Você é o assistente virtual de atendimento comercial da Gráfica Atuba. Seu tom é profissional, prestativo, cortês, ágil e comercial.
    O cliente enviou a seguinte mensagem ou foto de material gráfico: "{mensagem_cliente}"
    
    INSTRUÇÕES RÍGIDAS:
    1. Identifique o tipo de material gráfico na imagem ou mensagem (ex: cartões de visita, panfletos, faixas, adesivos, receituários).
    2. Ajude o cliente fornecendo orientações comerciais claras, tirando dúvidas sobre arquivos, prazos ou estimativas de impressão.
    3. Seja sempre muito cordial e incentive o fechamento do pedido ou o envio dos detalhes finais para produção.
    """

    parts = [{"text": prompt_texto}]
    if imagem_bytes and mime_type:
        img_b64 = base64.b64encode(imagem_bytes).decode("utf-8")
        parts.append({"inline_data": {"mime_type": mime_type, "data": img_b64}})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        res_json = response.json()
        if "candidates" in res_json and len(res_json["candidates"]) > 0:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"Erro na requisição Gemini: {e}")

    return (
        "Olá! Seja bem-vindo à *Gráfica Atuba*! 🖨️✨\n\n"
        "Recebemos o seu contato. Em que podemos ajudar com seus materiais impressos hoje?"
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
        remote_jid = key_data.get("remoteJid", "") if isinstance(key_data, dict) else {}
        phone = data.get("phone") or (str(remote_jid).split("@")[0] if "@" in str(remote_jid) else "")

        if not phone or "status" in str(data.get("event", "")).lower():
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
                user_message = img_data.get("caption", "Material gráfico enviado para orçamento")
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
        headers = {"apikey": API_KEY, "Content-Type": "application/json"}
        numero_limpo = "".join(filter(str.isdigit, str(phone)))
        payload_envio = {"number": numero_limpo, "text": resposta_bot}

        try:
            resp_envio = requests.post(url_envio, json=payload_envio, headers=headers, timeout=10)
            print(f"Status do Envio: {resp_envio.status_code}")
        except Exception as err_envio:
            print(f"Erro ao enviar requisição HTTP: {err_envio}")

        return "OK", 200
    except Exception as e:
        print(f"Erro no processamento do webhook: {e}")
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
