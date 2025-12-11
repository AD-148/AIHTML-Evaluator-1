import subprocess
import sys
import time
import requests
import os

def run_backend_and_test():
    # Start backend
    backend_dir = os.path.join(os.getcwd(), "backend")
    print(f"Starting backend from {backend_dir}...")
    
    # Using python -m uvicorn main:app
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    try:
        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(5)
        
        # Test endpoint
        url = "http://127.0.0.1:8000/evaluate"
        payload = {"html_content": "<div>test</div>"}
        
        print(f"Sending POST to {url}")
        try:
            response = requests.post(url, json=payload)
            print(f"Status Code: {response.status_code}")
            print(f"Content Type: {response.headers.get('content-type')}")
            print(f"Content Preview: {response.text[:200]}")
            
            try:
                json_resp = response.json()
                print("Response is valid JSON.")
            except:
                print("Response is NOT valid JSON.")
                
        except Exception as e:
            print(f"Request failed: {e}")
            
    finally:
        print("Killing backend...")
        process.terminate()
        stdout, stderr = process.communicate()
        if stdout: print(f"Backend STDOUT: {stdout.decode()}")
        if stderr: print(f"Backend STDERR: {stderr.decode()}")

if __name__ == "__main__":
    run_backend_and_test()
