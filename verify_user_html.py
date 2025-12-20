import asyncio
import os
from backend.advanced_analysis import AdvancedAnalyzer
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)

async def run_verification():
    # Read HTML from test_input.html
    file_path = r"C:\Users\USER\.gemini\antigravity\scratch\html_judge\reproduce_issue_survey.html"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please create it with your HTML content.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        user_html = f.read()

    print(f"Running AdvancedAnalyzer on {file_path}...")
    analyzer = AdvancedAnalyzer(user_html)
    
    # Run Async Analysis
    results = await analyzer.analyze()
    
    print("\n" + "="*50)
    print(" VERIFICATION RESULTS")
    print("="*50)

    # 1. VISUAL
    print("\n[1] VISUAL AGENT EVIDENCE:")
    print(results.get('visual', 'N/A'))
    
    # 2. MOBILE
    print("\n[2] MOBILE AGENT EVIDENCE (Simulation Logs):")
    print(results.get('mobile', 'N/A'))
    
    # 3. ACCESSIBILITY
    print("\n[3] ACCESSIBILITY AGENT EVIDENCE:")
    print(results.get('access', 'N/A'))

    # 4. FIDELITY
    print("\n[4] FIDELITY AGENT EVIDENCE:")
    print(results.get('fidelity', 'N/A'))

    # 5. TRACE
    print("\n[5] EXECUTION TRACE:")
    for step in results.get('trace', []):
        print(step)

if __name__ == "__main__":
    asyncio.run(run_verification())
