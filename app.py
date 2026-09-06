import os
from flask import Flask, request
from google import genai

app = Flask(__name__)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/", methods=["GET", "POST"])
def index():
    resp = "Faca sua pergunta abaixo."
    if request.method == "POST":
        p = request.form.get("msg")
        if p:
            try:
                r = client.models.generate_content(model="gemini-2.5-flash", contents=p)
                resp = r.text
            except Exception as e:
                resp = "Erro: " + str(e)
    
    return "<h2>Grafica Atuba</h2><form method='POST'><input name='msg' placeholder='Digite aqui...' required><button type='submit'>Enviar</button></form><p><b>Resposta:</b> " + resp + "</p>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
