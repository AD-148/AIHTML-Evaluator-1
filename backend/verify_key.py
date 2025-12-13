
import asyncio
import os
from dotenv import load_dotenv
from llm_service import analyze_chat

# Load environment variables
load_dotenv()

async def verify():
    print(f"Checking API Key: {os.getenv('OPENAI_API_KEY')[:10]}...") 
    
    # Create a dummy message
    messages = [{"role": "user", "content": "<div>Hello</div>"}]
    
    print("Sending request to LLM...")
    result = await analyze_chat(messages)
    
    print("\n--- Result ---")
    print(f"Final Judgement: {result.final_judgement}")
    print(f"Rationale: {result.rationale}")
    
    if "Error occurred" in result.rationale or "Mock" in result.rationale:
        print("\nFAILURE: Key verification failed or returned Mock data.")
    else:
        print("\nSUCCESS: Key verification passed.")

if __name__ == "__main__":
    asyncio.run(verify())
