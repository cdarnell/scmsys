#!/usr/bin/env python3
"""Debug script to test Tesla Fleet API and see detailed error responses."""

import json
import os
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

access_token = os.getenv("TESLA_ACCESS_TOKEN")
base = "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1"

if not access_token:
    print("ERROR: TESLA_ACCESS_TOKEN not found in .env")
    exit(1)

print(f"Testing Tesla Fleet API with token: {access_token[:50]}...")
print(f"Base URL: {base}\n")

# Try basic headers first
headers = {
    "Authorization": f"Bearer {access_token}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

print("=== Headers ===")
for k, v in headers.items():
    if k == "Authorization":
        print(f"{k}: Bearer {v.split()[-1][:50]}...")
    else:
        print(f"{k}: {v}")

print("\n=== Attempting GET /vehicles ===")
try:
    resp = requests.get(f"{base}/vehicles", headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    print(f"Headers: {dict(resp.headers)}")
    print(f"Body: {resp.text}")
    
    if resp.status_code >= 400:
        print(f"\nERROR Response:")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)
except Exception as e:
    print(f"Exception: {e}")

# Try with certificate if it exists
cert_path = "tesla_certificate.pem"
key_path = "tesla_private_key.pem"

if os.path.exists(cert_path) and os.path.exists(key_path):
    print(f"\n=== Attempting with Certificate ===")
    try:
        resp = requests.get(
            f"{base}/vehicles",
            headers=headers,
            cert=(cert_path, key_path),
            timeout=10
        )
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")
