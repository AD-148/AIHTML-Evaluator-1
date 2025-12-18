import asyncio
from backend.advanced_analysis import AdvancedAnalyzer
import logging

# Configure logging to see output in console
logging.basicConfig(level=logging.INFO)

html_content = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <h1>Hello</h1>
    <button>Click me</button>
</body>
</html>
"""

async def main():
    print("--- Starting Reproduction Script (Async) ---")
    analyzer = AdvancedAnalyzer(html_content)
    results = await analyzer.analyze()

    print("\n--- Execution Trace ---")
    for line in results.get("trace", []):
        print(line)

    print("\n--- End of Trace ---")

if __name__ == "__main__":
    asyncio.run(main())
