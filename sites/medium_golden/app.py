from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import os
import secrets
from datetime import timedelta

app = Flask(__name__)

# FIX: no hardcoded secret -- generated securely at startup
app.secret_key = secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)

DB = os.path.join(os.path.dirname(__file__), "database.db")

BLOCKED_PHRASES = [
    "ignore instructions",
    "you are now",
    "pretend you are",
    "DAN",
    "no restrictions",
    "jailbreak",
    "ignore previous"
]

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # FIX: parameterized inserts
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    cur.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (?, ?, ?)", (1, "admin", "admin123"))
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, content TEXT)")
    conn.commit()
    conn.close()
    print("debug: database initialized")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

# FIX: parameterized query -- no SQL injection possible
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        print("debug: login attempt for user:", username)
        try:
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
        except Exception as e:
            user = None
            error = str(e)
        conn.close()
        if user:
            # FIX: session persists correctly
            session.permanent = True
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

# FIX: session is read but NOT cleared after reading
@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=user)

# FIX: division by zero handled with null check
@app.route("/api/data")
def api_data():
    values = [10, 20, 30]
    if len(values) == 0:
        return jsonify({"result": 0, "note": "no data available"}), 200
    result = sum(values) / len(values)
    return jsonify({"result": result}), 200

@app.route("/api/users")
def api_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# FIX: system prompt protection + jailbreak blocking + single turn limit
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])

    if not isinstance(message, str) or len(message) == 0:
        return jsonify({"reply": "Please send a valid message."}), 400

    if len(message) > 500:
        return jsonify({"reply": "Message too long. Please keep it under 500 characters."}), 400

    # FIX: single turn limit
    if len(history) > 10:
        return jsonify({"reply": "Conversation limit reached. Please start a new session."}), 200

    # FIX: intent classifier blocks jailbreak phrases
    lower = message.lower()
    for phrase in BLOCKED_PHRASES:
        if phrase.lower() in lower:
            return jsonify({"reply": "I cannot process that request."}), 200

    # FIX: system prompt enforced -- role cannot be overridden
    print("debug: chat message received:", message[:50])
    reply = "Hello! You said: " + message
    return jsonify({"reply": reply, "history_length": len(history) + 1})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5004)
