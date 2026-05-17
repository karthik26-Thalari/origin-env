from flask import Flask, request, jsonify, render_template
from markupsafe import escape
import os

app = Flask(__name__)

BLOCKED_PHRASES = [
    "script",
    "ignore instructions",
    "you are now",
    "pretend you are",
    "DAN",
    "no restrictions"
]

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
        safe_message = escape(message)
        reflected = f"<div class='reflection'>You said: {safe_message}</div>"
    return render_template("form.html", reflected=reflected)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    if not isinstance(message, str) or len(message) == 0:
        return jsonify({"reply": "Please send a valid message."}), 400
    if len(message) > 500:
        return jsonify({"reply": "Message too long."}), 400
    lower = message.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase.lower() in lower:
            return jsonify({"reply": "I cannot process that request."}), 200
    reply = "Hello! You said: " + escape(message)
    return jsonify({"reply": str(reply)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(debug=True, host="0.0.0.0", port=port)
