import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENAI_API_KEY")

if key:
    print(f"Key found: {key[:5]}...{key[-5:] if len(key)>10 else ''}")
    print(f"Length: {len(key)}")
    print(f"Starts with sk-: {key.startswith('sk-')}")
else:
    print("No API Key found.")
