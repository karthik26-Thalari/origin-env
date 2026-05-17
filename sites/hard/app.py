from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import sqlite3
import os
from datetime import timedelta

app = Flask(__name__)

# VULNERABILITY: hardcoded credentials in plain text
SECRET_KEY = "supersecret123"
DB_USER = "admin"
DB_PASS = "password123"
DB_HOST = "localhost"
app.secret_key = SECRET_KEY

# BUG: permanent session with 0 second lifetime -- expires immediately
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(seconds=0)

DB = os.path.join(os.path.dirname(__file__), "database.db")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    # VULNERABILITY: raw SQL place 1
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    cur.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (1, 'admin', 'admin123', 'admin')")
    cur.execute("INSERT OR IGNORE INTO users (id, username, password, role) VALUES (2, 'user', 'user123', 'user')")
    cur.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, entry TEXT)")
    conn.commit()
    conn.close()
    print("debug: database initialized")  # LEGACY: was print "debug: database initialized"

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/health")
def health():
    print("debug: health check")  # LEGACY: was print "debug: health check"
    return jsonify({"status": "ok"}), 200

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = get_db()
        cur = conn.cursor()
        # VULNERABILITY: raw SQL place 2
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        print("debug: " + query)  # LEGACY: was print "debug: " + query
        try:
            cur.execute(query)
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
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)

# BUG: template references undefined user.profile_picture -- crashes on load
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    username = session.get("username", "unknown")
    user = {"username": username, "role": session.get("role", "user")}
    return render_template("dashboard.html", user=user)

# VULNERABILITY: ?admin=true bypasses session check entirely
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.args.get("admin") == "true":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, role FROM users")
        users = [dict(r) for r in cur.fetchall()]
        conn.close()
        return render_template("admin.html", users=users, bypass=True)
    if not session.get("logged_in") or session.get("role") != "admin":
        return jsonify({"error": "unauthorized"}), 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template("admin.html", users=users, bypass=False)

# VULNERABILITY: path traversal -- file param passed directly to open()
@app.route("/api/export")
def api_export():
    filename = request.args.get("file", "")
    print("debug: export requested for " + filename)  # LEGACY: was print "debug: ..."
    if not filename:
        return jsonify({"error": "no file specified"}), 400
    try:
        # VULNERABILITY: raw SQL place 3
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (entry) VALUES ('" + filename + "')")
        conn.commit()
        conn.close()
        with open(filename, "r") as f:
            contents = f.read()
        return render_template("export.html", filename=filename, contents=contents)
    except FileNotFoundError:
        return jsonify({"error": "file not found", "attempted_path": filename}), 404
    except Exception as e:
        return jsonify({"error": str(e), "attempted_path": filename}), 500

@app.route("/api/users")
def api_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

# VULNERABILITY: no turn limits, no role enforcement
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])
    print("debug: chat message received")  # LEGACY: was print "debug: ..."
    reply = "Hello! You said: " + str(message)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return jsonify({"reply": reply, "history": history})

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5002)
