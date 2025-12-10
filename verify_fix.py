import sys
import os
import time
import subprocess
import urllib.request
import json
import socket

def get_free_port():
    sock = socket.socket()
    sock.bind(('', 0))
    return sock.getsockname()[1]

def verify():
    port = get_free_port()
    # Path to main.py
    main_path = os.path.join(os.path.dirname(__file__), "backend", "main.py")
    
    # Start server
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(main_path)
    
    # We need to run uvicorn. Since main.py has uvicorn.run, we can just run main.py
    # But uvicorn.run inside main.py hardcodes port 8000.
    # We should run uvicorn via module to control port, or just rely on 8000 if free.
    # Let's try running main.py and hope 8000 is free, or edit main.py to use env var?
    # Simpler: Access localhost:8000. If it's busy, this might fail.
    # Given the user environment, let's assume 8000 is okay or just restart if needed.
    # Actually, better: run `uvicorn backend.main:app --port {port}`.
    
    cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)]
    cwd = os.path.dirname(os.path.dirname(main_path)) # root of project (one level up from backend?)
    # Layout is scratch/html_judge/backend/main.py. So wait,
    # c:\Users\USER\.gemini\antigravity\scratch\html_judge\backend\main.py
    # verification script will be in c:\Users\USER\.gemini\antigravity\scratch\html_judge\verify_fix.py
    # So run from c:\Users\USER\.gemini\antigravity\scratch\html_judge
    
    print(f"Starting server on port {port}...")
    proc = subprocess.Popen(cmd, cwd=os.getcwd(), stdout=sys.stdout, stderr=sys.stderr)
    
    try:
        # Wait for server to start
        for _ in range(20):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/")
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("Server failed to start.")
            return False

        print("Server started. Testing /evaluate endpoint...")
        
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/evaluate",
            data=json.dumps({"html_content": "<div>test</div>"}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as f:
                print(f"Success! Status: {f.status}")
                return True
        except urllib.error.HTTPError as e:
            print(f"HTTP Error: {e.code}")
            if e.code == 405:
                print("FAIL: Still getting 405 Method Not Allowed")
                return False
            else:
                print(f"Received {e.code}, which means routing is working (it reached the endpoint).")
                # 500 is fine (likely LLM error), 422 is fine (validation). 405 is the ONLY fail.
                return True
        except Exception as e:
            print(f"Unexpected error: {e}")
            return False
            
    finally:
        proc.terminate()
        proc.wait()

if __name__ == "__main__":
    if verify():
        print("VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)
