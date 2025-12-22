
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
    from backend.moengage_api import generate_html_from_stream
except ImportError:
    try:
        from moengage_api import generate_html_from_stream
    except ImportError:
        sys.path.append(os.path.join(os.getcwd(), 'backend'))
        from moengage_api import generate_html_from_stream

prompts = [
    "Create a simple button", 
    "Create a simple input field"
]

print("--- Starting Reproduction Test (With Logging) ---")

for i, p in enumerate(prompts):
    print(f"\n--- Processing Prompt {i+1}: {p} ---")
    # Use default session logic (hardcoded fallback)
    html, log = generate_html_from_stream(p)
    
    if html:
        print(f"Success! Length: {len(html)}")
    else:
        print(f"Failed! Log: {log}")
    
    time.sleep(2)

print("\n--- Test Finished ---")
