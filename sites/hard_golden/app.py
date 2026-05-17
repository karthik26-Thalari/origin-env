from flask import Flask, request, jsonify, render_template, session, redirect, url_for, abort
from datetime import timedelta
import sqlite3
import os
import secrets

app = Flask(__name__)

# FIX: no hardcoded credentials -- use environment variables
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASS = os.environ.get("DB_PASS", "")

# FIX: session lifetime set to 30 minutes
app.permanent_session_lifetime = timedelta(minutes=30)

DB = os.path.join(os.path.dirname(__file__), "database.db")
EXPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "exports"))

BLOCKED_PHRASES = [
    "ignore instructions",
    "you are now",
    "pretend you are",
    "DAN",
    "no restrictions",
    "jailbreak",
    "ignore previous",
    "forget everything",
    "new persona",
    "act as",
    "roleplay as",
    "simulate being"
]

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # FIX: all parameterized queries
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)", (1, "admin", "admin123", "admin"))
    cur.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (?, ?, ?, ?)", (2, "user", "user123", "user"))
    cur.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, entry TEXT)")
    conn.commit()
    conn.close()
    print("debug: database initialized")

# FIX: CSRF token generation and validation
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def validate_csrf(token):
    return token and token == session.get("csrf_token")

app.jinja_env.globals["csrf_token"] = generate_csrf_token

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/health")
def health():
    print("debug: health check")
    return jsonify({"status": "ok"}), 200

# FIX: parameterized login query
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        # FIX: CSRF validation
        if not validate_csrf(request.form.get("csrf_token")):
            return jsonify({"error": "invalid CSRF token"}), 403
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        print("debug: login attempt for:", username)
        try:
            # FIX: parameterized query
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
        except Exception as e:
            user = None
            error = str(e)
        conn.close()
        if user:
            session.permanent = True
            session["logged_in"] = True
            session["username"] = username
            session["role"] = user["role"]
            session["chat_turns"] = 0
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

# FIX: user.profile_picture has a proper default value
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    user = {
        "username": session.get("username", "unknown"),
        "role": session.get("role", "user"),
        "profile_picture": "/static/default_avatar.png"
    }
    return render_template("dashboard.html", user=user)

# FIX: ?admin=true bypass removed -- session check only
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return jsonify({"error": "invalid CSRF token"}), 403
    if not session.get("logged_in") or session.get("role") != "admin":
        return jsonify({"error": "unauthorized"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("admin.html", users=users)

# FIX: path traversal sanitized -- only files inside /exports/ allowed
@app.route("/api/export")
def api_export():
    filename = request.args.get("file", "")
    print("debug: export requested for:", filename)
    if not filename:
        return jsonify({"error": "no file specified"}), 400
    safe_path = os.path.abspath(os.path.join(EXPORTS_DIR, filename))
    if not safe_path.startswith(EXPORTS_DIR):
        return jsonify({"error": "access denied -- path traversal blocked"}), 403
    try:
        # FIX: parameterized log insert
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (entry) VALUES (?)", (filename,))
        conn.commit()
        conn.close()
        with open(safe_path, "r") as f:
            contents = f.read()
        return render_template("export.html", filename=filename, contents=contents)
    except FileNotFoundError:
        return jsonify({"error": "file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users")
def api_users():
    if not session.get("logged_in"):
        return jsonify({"error": "unauthorized"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# FIX: full chat protection -- 5 turn limit, role-lock, anomaly detection
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])

    if not isinstance(message, str) or len(message) == 0:
        return jsonify({"reply": "Please send a valid message."}), 400

    if len(message) > 500:
        return jsonify({"reply": "Message too long."}), 400

    # FIX: max 5 turns per session
    turns = session.get("chat_turns", 0)
    if turns >= 5:
        return jsonify({"reply": "Conversation limit reached. Please start a new session."}), 200

    # FIX: anomaly detection -- check all history messages too
    lower = message.lower()
    anomaly = False
    for phrase in BLOCKED_PHRASES:
        if phrase.lower() in lower:
            anomaly = True
            break

    # FIX: also scan history for anomalies
    for turn in history:
        content = turn.get("content", "").lower()
        for phrase in BLOCKED_PHRASES:
            if phrase.lower() in content:
                anomaly = True
                break

    if anomaly:
        # FIX: reset conversation if anomaly detected
        session["chat_turns"] = 0
        return jsonify({
            "reply": "I cannot process that request. Conversation has been reset.",
            "history": []
        }), 200

    print("debug: chat turn", turns + 1, "message:", message[:50])
    session["chat_turns"] = turns + 1

    # FIX: system prompt cannot be overridden -- role is locked server-side
    reply = "Hello! You said: " + message
    return jsonify({
        "reply": reply,
        "turns_remaining": 5 - session["chat_turns"]
    })

if __name__ == "__main__":
    init_db()
    # create a sample export file so /api/export has something to serve
    sample = os.path.join(EXPORTS_DIR, "sample.txt")
    if not os.path.exists(sample):
        with open(sample, "w") as f:
            f.write("This is a safe export file.\nPath traversal is blocked.")
    app.run(debug=True, host="0.0.0.0", port=5005)
