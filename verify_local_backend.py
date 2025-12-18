import sys
import os

# Add root to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import backend.main...")
    from backend.main import app
    print("SUCCESS: backend.main imported successfully.")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")
