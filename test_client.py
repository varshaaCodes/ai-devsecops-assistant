import requests

BASE_URL = "http://127.0.0.1:8000"

# Test review endpoint
review_payload = {"code": "print('Hello')"}
review_response = requests.post(f"{BASE_URL}/review", json=review_payload)
print("Review Endpoint Response:", review_response.json())

# Test scan endpoint
scan_payload = {"code": "password = '1234'"}
scan_response = requests.post(f"{BASE_URL}/scan", json=scan_payload)
print("Scan Endpoint Response:", scan_response.json())
