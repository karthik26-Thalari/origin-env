import pytest
import subprocess
import sys
import time
import os
import tempfile
import shutil
import requests


def _wait_for_server(url, retries=20, delay=0.5):
    for _ in range(retries):
        try:
            r = requests.get(url + "/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


@pytest.fixture(scope="session")
def easy_site():
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="sites/easy",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "FLASK_RUN_PORT": "5001", "PORT": "5001"},
    )
    url = "http://localhost:5001"
    if not _wait_for_server(url):
        proc.kill()
        pytest.fail("easy_site failed to start on port 5001")
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture(scope="session")
def medium_site():
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd="sites/medium",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "FLASK_RUN_PORT": "5002", "PORT": "5002"},
    )
    url = "http://localhost:5002"
    if not _wait_for_server(url):
        proc.kill()
        pytest.fail("medium_site failed to start on port 5002")
    yield url
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


@pytest.fixture()
def temp_snapshot_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)
