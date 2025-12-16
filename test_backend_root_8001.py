import requests
import sys

url = "http://127.0.0.1:8001/"

print(f"Sending GET request to {url}...")
try:
    response = requests.get(url, timeout=5)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
