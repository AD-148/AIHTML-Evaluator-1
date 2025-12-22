
import sys
import os
import time
import logging

from dotenv import load_dotenv

# Load env vars first
load_dotenv(os.path.join("backend", ".env"))

# Configure logging to see internal messages
logging.basicConfig(level=logging.INFO)

# Ensure backend logic is importable
sys.path.append(os.path.abspath("backend"))

try:
    from backend.moengage_api import generate_html_from_stream, create_new_session
except ImportError:
    try:
        from moengage_api import generate_html_from_stream, create_new_session
    except ImportError:
        sys.path.append(os.path.join(os.getcwd(), 'backend'))
        from moengage_api import generate_html_from_stream, create_new_session

prompts = [
    "Create a simple button", 
    "Create a simple input field"
]

print("--- Starting Reproduction Test (Dynamic Sessions) ---")

for i, p in enumerate(prompts):
    print(f"\n--- Processing Prompt {i+1}: {p} ---")
    
    # 1. Create Session
    session_id = create_new_session()
    print(f"Created Session: {session_id}")
    
    if session_id:
        # 2. Generate
        html, log = generate_html_from_stream(p, session_id=session_id)
        
        if html:
            print(f"Success! Length: {len(html)}")
        else:
            print(f"Failed! Log: {log}")
    else:
        print("Failed to create session.")
    
    time.sleep(2)

print("\n--- Test Finished ---")
