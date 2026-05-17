"""
revert_system.py -- Trident ENV v3.0
"""

import os
import json
import shutil
import subprocess
import time
import platform
from datetime import datetime

import requests


def _safe_copytree(src: str, dst: str):
    """Replace dst with src atomically -- works around Windows handle locks."""
    dst_old = dst + "_old_" + str(int(time.time()))
    if os.path.exists(dst):
        os.rename(dst, dst_old)
    shutil.copytree(src, dst)
    if os.path.exists(dst_old):
        shutil.rmtree(dst_old, ignore_errors=True)


class RevertSystem:

    def __init__(self, site_path: str, golden_state_path: str,
                 base_url: str = "http://localhost:5000"):
        self.site_path         = site_path
        self.golden_state_path = golden_state_path
        self.base_url          = base_url.rstrip("/")
        self.revert_history    = []
        self.flask_process     = None
        self.snapshot_dir      = "snapshots"

    def snapshot(self) -> str:
        os.makedirs(self.snapshot_dir, exist_ok=True)
        snapshot_id  = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        snapshot_dst = os.path.join(self.snapshot_dir, snapshot_id)
        shutil.copytree(self.site_path, snapshot_dst)
        all_snaps = sorted(os.listdir(self.snapshot_dir))
        while len(all_snaps) > 5:
            oldest = os.path.join(self.snapshot_dir, all_snaps.pop(0))
            shutil.rmtree(oldest, ignore_errors=True)
        return snapshot_id

    def _kill_existing_flask(self):
        if self.flask_process is not None:
            try:
                self.flask_process.terminate()
                self.flask_process.wait(timeout=3)
            except Exception:
                try:
                    self.flask_process.kill()
                except Exception:
                    pass
            self.flask_process = None
        if platform.system() != "Windows":
            subprocess.run(["pkill", "-f", "app.py"],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)

    def _start_flask(self) -> bool:
        self._kill_existing_flask()
        time.sleep(0.5)
        self.flask_process = subprocess.Popen(
            ["python", "app.py"],
            cwd=self.site_path,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(15):
            try:
                resp = requests.get(f"{self.base_url}/health", timeout=1)
                if resp.status_code == 200:
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.5)
        return False

    def standard_revert(self, snapshot_id: str) -> bool:
        snapshot_src = os.path.join(self.snapshot_dir, snapshot_id)
        self._kill_existing_flask()
        _safe_copytree(snapshot_src, self.site_path)
        result = self._start_flask()
        self.revert_history.append({
            "type":            "STANDARD_REVERT",
            "timestamp":       datetime.now().isoformat(),
            "snapshot_id":     snapshot_id,
            "flask_recovered": result,
        })
        print(f"STANDARD_REVERT triggered at {datetime.now()}")
        return result

    def softlock(self, reason: str) -> bool:
        flag_path = os.path.join(self.site_path, "softlock_active.flag")
        open(flag_path, "w").close()
        log_dir  = "logs"
        log_path = os.path.join(log_dir, "intrusion_log.json")
        os.makedirs(log_dir, exist_ok=True)
        log_entry = {
            "timestamp":          datetime.now().isoformat(),
            "reason":             reason,
            "severity":           "HIGH",
            "softlock_triggered": True,
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"SOFTLOCK triggered: {reason}")
        time.sleep(5)
        result = self.load_golden_state()
        if os.path.exists(flag_path):
            os.remove(flag_path)
        self.revert_history.append({
            "type":      "SOFTLOCK",
            "timestamp": datetime.now().isoformat(),
            "reason":    reason,
            "recovered": result,
        })
        return result

    def delete_and_restore(self) -> bool:
        print("DELETE triggered -- wiping site")
        self._kill_existing_flask()
        _safe_copytree(self.golden_state_path, self.site_path)
        result = self._start_flask()
        self.revert_history.append({
            "type":      "DELETE",
            "timestamp": datetime.now().isoformat(),
            "recovered": result,
        })
        return result

    def load_golden_state(self) -> bool:
        self._kill_existing_flask()
        _safe_copytree(self.golden_state_path, self.site_path)
        result = self._start_flask()
        print(f"GOLDEN STATE loaded -- Flask recovered: {result}")
        return result

    def get_revert_history(self) -> list:
        return list(self.revert_history)


def add_softlock_middleware(app, site_path: str):
    @app.before_request
    def check_softlock():
        flag = os.path.join(site_path, "softlock_active.flag")
        if os.path.exists(flag):
            from flask import jsonify
            return jsonify({"error": "locked", "mode": "SOFTLOCK"}), 403
        return None


if __name__ == "__main__":
    print("RevertSystem loaded OK -- run test_trident.py for full tests")
