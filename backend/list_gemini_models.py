import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in .env")
        return

    genai.configure(api_key=api_key)
    
    print(f"Checking models for API Key: {api_key[:8]}...")
    try:
        print("\nAvailable Models:")
        found_pro = False
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                if "gemini-1.5-pro" in m.name:
                    found_pro = True
        
        print("\n-------------------")
        if found_pro:
            print("SUCCESS: 'gemini-1.5-pro' IS available.")
        else:
            print("WARNING: 'gemini-1.5-pro' NOT found. You might only have access to 'gemini-1.5-flash' or 'gemini-pro'.")
            
    except Exception as e:
        print(f"ERROR: Could not list models. {e}")

if __name__ == "__main__":
    list_models()
