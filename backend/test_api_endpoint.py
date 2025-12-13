
import requests
import json
import sys

def test_endpoint():
    url = "http://127.0.0.1:8000/evaluate"
    payload = {
        "messages": [
            {"role": "user", "content": "<div>Test</div>"}
        ]
    }
    
    print(f"Testing API at {url}...")
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        print("Response Headers:", response.headers)
        
        try:
            data = response.json()
            print("\nResponse Body (JSON):")
            print(json.dumps(data, indent=2))
        except json.JSONDecodeError:
            print("\nResponse is NOT valid JSON:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to localhost:8000. Is the backend running?")
    except Exception as e:
        print(f"\nERROR: {e}")

if __name__ == "__main__":
    test_endpoint()
