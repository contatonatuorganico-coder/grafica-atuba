import os
from flask import Flask, request
from google import genai

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=["GET", "POST"])
def index():
    resposta = "Digite sua duvida acima."
    if request.method == "POST":
        pergunta = request.form.get("pergunta")
        if pergunta:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=pergunta,
            )
            resposta = response.text
            
    return f"""
    <h2>Grafica Atuba - IA</h2>
    <form method="POST">
        <input type="text" name="pergunta" placeholder="Digite aqui..." required>
        <button type="submit">Enviar</button>
    </form>
    <p><b>Resposta:</b> {resposta}</p>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
