"""Start PropAdmin API and frontend from one terminal on Windows/macOS/Linux."""
from pathlib import Path
import os, shutil, subprocess, sys, threading, time

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
VENV = BACKEND / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def run_npm(*args):
    cmd = ["cmd", "/c", "npm", *args] if os.name == "nt" else ["npm", *args]
    subprocess.run(cmd, cwd=FRONTEND, check=True)

def setup():
    if not (BACKEND / "main.py").exists() or not (FRONTEND / "package.json").exists():
        raise RuntimeError("Run this script from the extracted project root; backend and frontend folders must exist.")
    if not shutil.which("python") and not shutil.which("py"):
        raise RuntimeError("Python was not found. Install Python 3.10+ and enable Add Python to PATH.")
    if not shutil.which("npm"):
        raise RuntimeError("npm was not found. Install Node.js 18+ and reopen PowerShell.")
    if not PY.exists():
        subprocess.run([shutil.which("python") or shutil.which("py"), "-m", "venv", str(VENV)], check=True)
    subprocess.run([str(PY), "-m", "pip", "install", "-r", str(BACKEND / "requirements.txt")], check=True)
    if not (FRONTEND / "node_modules").exists():
        run_npm("install")

def pump(label, proc):
    for line in iter(proc.stdout.readline, ""):
        print(f"[{label}] {line.rstrip()}", flush=True)

def main():
    try:
        setup()
    except (RuntimeError, subprocess.CalledProcessError) as e:
        print(f"\n[SETUP ERROR] {e}")
        return 1
    cmds = [
        ("BACKEND", [str(PY), "-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], BACKEND),
        ("FRONTEND", (["cmd", "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1"] if os.name == "nt" else ["npm", "run", "dev", "--", "--host", "127.0.0.1"]), FRONTEND),
    ]
    procs = []
    try:
        for label, cmd, cwd in cmds:
            p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
            procs.append((label, p))
            threading.Thread(target=pump, args=(label, p), daemon=True).start()
        print("\nPropAdmin is starting. Frontend: http://localhost:5173 | API docs: http://127.0.0.1:8000/docs")
        print("Keep this terminal open. Press Ctrl+C to stop both services.\n")
        while True:
            for label, p in procs:
                code = p.poll()
                if code is not None:
                    print(f"[{label}] stopped with code {code}")
                    return code
            time.sleep(.3)
    except KeyboardInterrupt:
        print("\nStopping PropAdmin...")
    finally:
        for _, p in procs:
            if p.poll() is None: p.terminate()
        for _, p in procs:
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
