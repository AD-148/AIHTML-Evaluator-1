import requests
import json
import sys

url = "http://127.0.0.1:8000/evaluate"
payload = {
    "messages": [
        {"role": "user", "content": "<h1>Test</h1>"}
    ]
}
headers = {"Content-Type": "application/json"}

print(f"Sending POST request to {url}...")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
