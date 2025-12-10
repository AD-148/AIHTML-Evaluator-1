import subprocess
import sys
import os
import shutil

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(base_dir, "backend")
    frontend_dir = os.path.join(base_dir, "frontend")

    # 1. Setup Backend
    print(f"Starting Backend in {backend_dir}...")
    backend_cmd = [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--port", "8000"]
    subprocess.Popen(
        backend_cmd,
        cwd=backend_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    # 2. Setup Frontend
    print(f"Starting Frontend in {frontend_dir}...")
    
    # Try to find npm, if not found, add common path
    npm_path = shutil.which("npm")
    env = os.environ.copy()
    
    if not npm_path:
        # Fallback to known location
        node_dir = r"C:\Program Files\nodejs"
        if os.path.exists(node_dir):
            env["PATH"] = node_dir + os.pathsep + env["PATH"]
            print(f"Added {node_dir} to PATH for this session.")
    
    # On Windows, npm is usually npm.cmd
    subprocess.Popen(
        ["npm.cmd", "run", "dev"],
        cwd=frontend_dir,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
        shell=True 
    )

    print("\n---------------------------------------------------")
    print("Services Launching...")
    print("Backend API: http://127.0.0.1:8000")
    print("Frontend UI: http://localhost:5173")
    print("---------------------------------------------------")
    print("If windows close immediately, check for errors in them.")
    input("Press Enter to exit this launcher (servers will keep running)...")

if __name__ == "__main__":
    main()
