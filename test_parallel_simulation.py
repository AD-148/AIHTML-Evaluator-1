
import threading
import time
import sys
import os

import logging
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
    "Create a red button",
    "Create a blue button",
    "Create a green button"
]

def process_prompt(p, index):
    print(f"[{index}] Starting: {p}")
    try:
        # 1. Create unique session
        session_id = create_new_session()
        print(f"[{index}] Session: {session_id}")
        
        if not session_id:
            print(f"[{index}] FAILED to create session")
            return

        # 2. Generate
        html, log = generate_html_from_stream(p, session_id=session_id)
        
        if html:
            print(f"[{index}] ✅ Success! Length: {len(html)}")
        else:
            print(f"[{index}] ❌ Failed! Log: {log}")
            
    except Exception as e:
        print(f"[{index}] Exception: {e}")


print("--- Starting Single Request Test ---")
process_prompt("Test Prompt Single", 0)

