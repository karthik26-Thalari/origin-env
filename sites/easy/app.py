from flask import Flask, request, jsonify, render_template_string, render_template
import os

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/form", methods=["GET", "POST"])
def form():
    reflected = None
    if request.method == "POST":
        message = request.form.get("message", "")
        reflected = render_template_string(
            "<div class='reflection'>You said: " + message + "</div>"
        )
    return render_template("form.html", reflected=reflected)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    reply = "Hello! You said: " + str(message)
    return jsonify({"reply": reply})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

# TEST_MODIFICATION_MARKER
