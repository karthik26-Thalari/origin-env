from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

SECRET_KEY = "password123"
app.secret_key = SECRET_KEY

DB = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)")
    cur.execute("INSERT OR IGNORE INTO users (id, username, password) VALUES (1, 'admin', 'admin123')")
    cur.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, content TEXT)")
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        print("debug:", query)
        try:
            cur.execute(query)
            user = cur.fetchone()
        except Exception as e:
            user = None
            error = str(e)
        conn.close()
        if user:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

@app.route("/dashboard")
def dashboard():
    user = session.get("user")
    session.clear()
    if not user:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=user)

@app.route("/api/data")
def api_data():
    values = []
    result = sum(values) / len(values)
    return jsonify({"result": result})

@app.route("/api/users")
def api_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])
    print("debug:", message)
    reply = "Hello! You said: " + str(message)
    return jsonify({"reply": reply, "history_length": len(history)})

if __name__ == "__main__":
    init_db()
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))

