
import requests
import json

HTML = """<!DOCTYPE html>
<html lang="en">
(truncated for brevity, using same header as user provided)
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body>
    <button>Test</button>
</body>
</html>"""

# I'll use the FULL HTML from the user request to be safe
HTML = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feedback Survey</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        :root {
            --color-primary-main: #0D6EFD;
        } 
        /* ... simplified css for length ... */
    </style>
</head>

<body class="bg-black bg-opacity-50 flex items-center justify-center p-4">
    <div id="main-container">
       <button id="yes-button">Yes</button>
    </div>
</body>
</html>"""

# Actually, let's use the EXACT content if possible to catch parsers issues
# But for now, let's just trigger the endpoint.

url = "http://127.0.0.1:8000/evaluate"

payload = {
    "messages": [
        {"role": "user", "content": HTML}
    ]
}
headers = {"Content-Type": "application/json"}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error Response: {response.text}")
    data = response.json()
    print("\n--- TRACE ---")
    for t in data.get("execution_trace", []):
        print(t)
except Exception as e:
    print(f"Failed: {e}")
