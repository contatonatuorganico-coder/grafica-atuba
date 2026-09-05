import os
from flask import Flask, render_template, request
from google import genai

app = Flask(__name__)

# Pega a chave direto das configurações do Render com segurança
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=["GET", "POST"])
def index():
    resposta = ""
    if request.method == "POST":
        pergunta = request.form.get("pergunta")
        if pergunta:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=pergunta,
            )
            resposta = response.text
            
    return f\"\"\"
    <html>
        <head><title>Gráfica Atuba</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>Gráfica Atuba - Assistente IA</h2>
            <form method="POST">
                <input type=\"text\" name=\"pergunta\" placeholder=\"Digite sua dúvida...\" style=\"width: 300px; padding: 5px;\" required>
                <button type=\"submit\" style=\"padding: 5px 10px;\">Enviar</button>
            </form>
            <p style=\"margin-top: 20px; white-space: pre-wrap;\"><b>Resposta:</b> {resposta}</p>
        </body>
    </html>
    \"\"\"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
  
