import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("FAILURE: GEMINI_API_KEY not found in .env")
        return

    print(f"Testing Key: {api_key[:10]}... (Length: {len(api_key)})")
    
    try:
        genai.configure(api_key=api_key)
        # Use a model from the list
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        print("Sending prompt to Gemini...")
        response = model.generate_content("Return a JSON object with a greeting key saying 'Hello Gemini'.")
        
        print("SUCCESS: Connected to Gemini.")
        print("Response:", response.text)
    except Exception as e:
        print("FAILURE: Could not connect to Gemini.")
        print("Error:", str(e))

if __name__ == "__main__":
    test_gemini()
