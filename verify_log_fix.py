
import asyncio
from backend.advanced_analysis import AdvancedAnalyzer

html_content = """
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <!-- Violation: Image missing alt -->
    <img src="test.jpg" />
    <!-- Violation: Button missing accessible name -->
    <button></button>
</body>
</html>
"""

async def main():
    print("Starting Analysis...")
    analyzer = AdvancedAnalyzer(html_content)
    results = await analyzer.analyze()
    print("\n\n--- EXECUTION TRACE ---")
    for log in results.get("trace", []):
        if "Accessibility Audit" in log:
            print(log)

if __name__ == "__main__":
    asyncio.run(main())
