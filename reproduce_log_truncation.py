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

print("--- Starting Reproduction Script ---")
analyzer = AdvancedAnalyzer(html_content)
results = analyzer.analyze()

print("\n--- Execution Trace ---")
for line in results.get("trace", []):
    print(line)

print("\n--- End of Trace ---")
