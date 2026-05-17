import os
import json
import threading
from datetime import datetime
from flask import request, jsonify

ENTRY_B_ROUTES = ["/admin", "/api/internal", "/root", "/system", "/superuser", "/backdoor"]

status_state = {
    "episode": 0,
    "task_mode": "LEGACY",
    "last_reward": 0.0,
    "revert_count": 0,
    "golden_state_loads": 0
}

def _log_intrusion(site_path: str):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "intrusion_log.json")
    entry = {
        "timestamp": datetime.now().isoformat(),
        "source_ip": request.remote_addr,
        "user_agent": request.user_agent.string,
        "path": request.path,
        "method": request.method,
        "attack_classification": "UNAUTHORIZED_ENTRY",
        "severity": "HIGH",
        "softlock_triggered": True
    }
    records = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                records = json.load(f)
        except (json.JSONDecodeError, IOError):
            records = []
    records.append(entry)
    with open(log_path, "w") as f:
        json.dump(records, f, indent=2)

def _count_intrusions() -> int:
    log_path = os.path.join("logs", "intrusion_log.json")
    if not os.path.exists(log_path):
        return 0
    try:
        with open(log_path, "r") as f:
            records = json.load(f)
        return len(records)
    except (json.JSONDecodeError, IOError):
        return 0

def add_entry_guard(app, site_path: str, revert_system=None):

    @app.before_request
    def entry_guard():
        if request.path in ENTRY_B_ROUTES:
            _log_intrusion(site_path)
            if revert_system is not None:
                threading.Thread(
                    target=revert_system.softlock,
                    args=("unauthorized_entry_b: " + request.path,)
                ).start()
            return jsonify({
                "error": "access_denied",
                "mode": "SOFTLOCK_TRIGGERED",
                "path": request.path
            }), 403

        flag_path = os.path.join(site_path, "softlock_active.flag")
        if os.path.exists(flag_path):
            return jsonify({
                "error": "site_locked",
                "mode": "SOFTLOCK_ACTIVE"
            }), 403

        return None

    @app.route("/trident/status")
    def trident_status():
        flag_path = os.path.join(site_path, "softlock_active.flag")
        mode = "SOFTLOCK" if os.path.exists(flag_path) else "NORMAL"
        return jsonify({
            "mode": mode,
            "episode": status_state["episode"],
            "task_mode": status_state["task_mode"],
            "last_reward": status_state["last_reward"],
            "revert_count": status_state["revert_count"],
            "golden_state_loads": status_state["golden_state_loads"],
            "intrusion_attempts": _count_intrusions()
        })

if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    add_entry_guard(app, "sites/easy")

    @app.route("/")
    def index():
        return "OK", 200

    print("Test: GET /admin should return 403")
    print("Test: GET / should return 200")
    app.run(port=5001, debug=False)
