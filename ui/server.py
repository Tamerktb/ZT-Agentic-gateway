"""
Dashboard server — starts all Zero Trust services and serves the web UI.
Opens the browser automatically. Stop with Ctrl+C.

Usage: python server.py
"""
import os, sys, time, subprocess, threading, webbrowser
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

BASE = Path(__file__).parent.parent
SERVICES = [
    ("identity-provider", 8001, BASE / "services/identity-provider"),
    ("credential-vault", 8002, BASE / "services/credential-vault"),
    ("policy-engine", 8003, BASE / "services/policy-engine"),
    ("audit-service", 8004, BASE / "services/audit-service"),
    ("ai-gateway", 8000, BASE / "services/ai-gateway"),
]

env = os.environ.copy()
env.update({"JWT_SECRET": "zt-lab-secret-change-in-prod", "PYTHONIOENCODING": "utf-8",
    "IDENTITY_PROVIDER_URL": "http://127.0.0.1:8001",
    "CREDENTIAL_VAULT_URL": "http://127.0.0.1:8002",
    "POLICY_ENGINE_URL": "http://127.0.0.1:8003",
    "AUDIT_SERVICE_URL": "http://127.0.0.1:8004"})

procs = []

def start_services():
    print("Starting services...")
    for name, port, cwd in SERVICES:
        p = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.main:app",
            "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=str(cwd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p)
        print(f"  {name}:{port} (PID {p.pid})")
    time.sleep(3)
    import httpx
    for name, port, _ in SERVICES:
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2)
            status = "OK" if r.status_code == 200 else "FAIL"
        except:
            status = "FAIL"
        print(f"  [{status}] {name}:{port}")

def stop_services():
    for p in procs:
        p.terminate()
    print("\nServices stopped.")

def main():
    start_services()
    port = 8080
    ui_dir = BASE / "ui"
    os.chdir(str(ui_dir))
    server = HTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"\nDashboard: {url}")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
        stop_services()

if __name__ == "__main__":
    main()
