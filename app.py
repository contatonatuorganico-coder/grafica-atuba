import base64
import os
import requests
import google.generativeai as genai
from flask import Flask, request

app = Flask(__name__)

# Memória temporária para guardar os números pausados
ATENDIMENTO_HUMANO = set()

# Variáveis de Ambiente
EVOLUTION_URL = os.environ.get("EVOLUTION_API_URL", "https://evolution-api-production-5008.up.railway.app").rstrip("/")
EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE_NAME", "grafica-atuba")
API_KEY = os.environ.get("EVOLUTION_API_KEY", "5F1D6E603161-4C5D-9DBA-7A59564694BF")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Mensagem Padrão de Boas-Vindas e Apresentação
MENSAGEM_BOAS_VINDAS = (
    "Olá! Seja bem-vindo(a) à **Gráfica Atuba**! 🖨️✨\n\n"
    "Sou o assistente virtual e posso te ajudar com orçamentos rápidos de:\n"
    "• Cartões de Visita\n"
    "• Panfletos / Flyers\n"
    "• Banners em Lona\n"
    "• Adesivos Personalizados\n"
    "• Blocos de Pedidos / Talões\n\n"
    "Como posso te ajudar hoje?\n"
    "*(Se preferir falar direto com nossa equipe, basta digitar *falar com atendente* a qualquer momento).*"
)

def enviar_mensagem_whatsapp(numero, texto):
    """Função auxiliar para enviar mensagens via Evolution API"""
    url_envio = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {
        "apikey": API_KEY,
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload_envio = {
        "number": str(numero),
        "text": texto,
        "delay": 2000
    }
    try:
        resp = requests.post(url_envio, json=payload_envio, headers=headers, timeout=15)
        if resp.status_code not in [200, 201]:
            numero_limpo = "".join(filter(str.isdigit, str(numero)))
            requests.post(url_envio, json={"number": numero_limpo, "text": texto, "delay": 2000}, headers=headers, timeout=15)
    except Exception as err:
        print(f"Erro ao enviar mensagem: {err}", flush=True)

def processar_resposta(mensagem_cliente, imagem_bytes=None, mime_type=None):
    msg_limpa = mensagem_cliente.strip().lower()

    # Se for apenas saudação inicial, entrega a apresentação completa imediatamente
    saudacoes = ["oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "inicio", "início"]
    if msg_limpa in saudacoes:
        return MENSAGEM_BOAS_VINDAS

    if not GEMINI_API_KEY:
        print(">>> AVISO: GEMINI_API_KEY não configurada no Render!", flush=True)
        return MENSAGEM_BOAS_VINDAS

    prompt_sistema = f"""
    Você é o assistente virtual comercial da **Gráfica Atuba**.
    Seu objetivo é atender os clientes no WhatsApp de forma clara, objetiva e amigável.

    APRESENTAÇÃO PADRÃO DA EMPRESA:
    {MENSAGEM_BOAS_VINDAS}

    TABELA DE PREÇOS DE REFERÊNCIA:
    1. Cartão de Visita (Couché 300g, 9x5cm, Verniz UV):
       - 500 unidades: R$ 95,00 | 1.000 unidades: R$ 140,00
    2. Panfletos / Flyers (Couché 115g, 10x14cm, 4x0 cores):
       - 1.000 un: R$ 180,00 | 2.500 un: R$ 260,00 | 5.000 un: R$ 390,00
    3. Banners em Lona 440g (com bastão, ponteira e cordão):
       - Tam. 0,60 x 0,90m: R$ 75,00 | 0,70 x 1,00m: R$ 95,00 | 1,00 x 1,50m: R$ 160,00
    4. Adesivos Personalizados (Vinil Brilho/Fosco):
       - 100 un (5x5cm): R$ 65,00 | 500 un (5x5cm): R$ 150,00
    5. Bloco de Pedidos / Talões (2 vias, 50 jogos cada):
       - 5 talões A5: R$ 130,00 | 10 talões A5: R$ 210,00

    INSTRUÇÕES DE RESPOSTA:
    - Se a mensagem for saudação simples, utilize a Apresentação Padrão.
    - Dê preços diretos da tabela de acordo com o pedido.
    - Se perguntarem sobre arte: informe que criamos a arte ou verificamos o arquivo enviado.
    - Mantenha respostas curtas e legíveis no celular.
    """

    modelos_para_testar = [
        "gemini-3.6-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]

    for nome_modelo in modelos_para_testar:
        try:
            model = genai.GenerativeModel(nome_modelo)
            conteudos = [{"role": "user", "parts": [prompt_sistema, f"Mensagem do cliente: {mensagem_cliente}"]}]

            if imagem_bytes and mime_type:
                conteudos[0]["parts"].append({"mime_type": mime_type, "data": imagem_bytes})

            response = model.generate_content(conteudos)
            if response and response.text:
                print(f">>> SUCESSO com o modelo: {nome_modelo}", flush=True)
                return response.text
        except Exception as e:
            print(f">>> FALHA com o modelo {nome_modelo}: {e}", flush=True)

    # Retorno de segurança (Fallback) atualizado com a apresentação completa
    return MENSAGEM_BOAS_VINDAS

@app.route("/", methods=["GET"])
def home():
    return "Grafica Atuba - IA Ativa!"

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
        imagem_bytes = None
        mime_type = None

        if isinstance(message_obj, dict):
            if "conversation" in message_obj:
                user_message = message_obj["conversation"]
            elif "extendedTextMessage" in message_obj and isinstance(message_obj["extendedTextMessage"], dict):
                user_message = message_obj["extendedTextMessage"].get("text", "")
            elif "imageMessage" in message_obj and isinstance(message_obj["imageMessage"], dict):
                img_data = message_obj["imageMessage"]
                user_message = img_data.get("caption", "Foto enviada para orçamento")
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

        msg_clean = user_message.strip().lower()

        # ==========================================
        # GERENCIAMENTO DE COMANDOS DE PAUSA/VOLTAR
        # ==========================================
        
        gatilhos_pausa = [
            "#pausa", "#pausar", "#atendente", "#humano",
            "falar com atendente", "falar com humano", "atendente", "humano",
            "quer falar com atendente", "quero falar com atendente", "falar com uma pessoa"
        ]

        if msg_clean in gatilhos_pausa:
            ATENDIMENTO_HUMANO.add(remote_jid)
            enviar_mensagem_whatsapp(remote_jid, "⏸️ *Atendimento automático pausado.* Um de nossos atendentes dará continuidade ao seu atendimento em instantes!")
            return "OK", 200

        if msg_clean in ["#voltar", "#ia", "#bot", "voltar ia"]:
            ATENDIMENTO_HUMANO.discard(remote_jid)
            enviar_mensagem_whatsapp(remote_jid, "🤖 *Atendimento automático reativado!* Como posso te ajudar?")
            return "OK", 200

        if is_from_me:
            return "OK", 200

        if remote_jid in ATENDIMENTO_HUMANO:
            return "OK", 200

        if not user_message and not imagem_bytes:
            return "OK", 200

        # ==========================================

        resposta_bot = processar_resposta(user_message, imagem_bytes=imagem_bytes, mime_type=mime_type)
        enviar_mensagem_whatsapp(remote_jid, resposta_bot)

        return "OK", 200
    except Exception as e:
        print(f"Erro no webhook: {e}", flush=True)
        return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
