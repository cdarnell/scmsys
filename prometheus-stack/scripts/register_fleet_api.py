#!/usr/bin/env python3
"""
Register with Tesla Fleet API.

This script:
1. Generates an EC public key (secp256r1 curve)
2. Hosts it at .well-known/appspecific/com.tesla.3p.public-key.pem
3. Registers the account with Tesla Fleet API
4. Verifies registration with the public_key endpoint
"""

import os
import json
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from dotenv import load_dotenv

load_dotenv()

# Configuration
TESLA_CLIENT_ID = os.getenv("TESLA_CLIENT_ID")
TESLA_CLIENT_SECRET = os.getenv("TESLA_CLIENT_SECRET")
TESLA_ACCESS_TOKEN = os.getenv("TESLA_ACCESS_TOKEN")
REDIRECT_HOST = os.getenv("REDIRECT_HOST", "sentiently-thigmotactic-desirae.ngrok-free.dev")
FLEET_API_BASE = "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1"

# Keys and paths
PRIVATE_KEY_PATH = "tesla_ec_private_key.pem"
PUBLIC_KEY_PATH = "tesla_ec_public_key.pem"
WELL_KNOWN_DIR = ".well-known/appspecific"
WELL_KNOWN_PUB_KEY = os.path.join(WELL_KNOWN_DIR, "com.tesla.3p.public-key.pem")


def generate_ec_keys():
    """Generate EC key pair with secp256r1 curve."""
    print("[*] Generating EC key pair (secp256r1 curve)...")
    
    # Generate private key
    private_key = ec.generate_private_key(
        ec.SECP256R1(), default_backend()
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    # Save keys
    with open(PRIVATE_KEY_PATH, 'wb') as f:
        f.write(private_pem)
    print(f"✓ Private key saved to {PRIVATE_KEY_PATH}")
    
    with open(PUBLIC_KEY_PATH, 'wb') as f:
        f.write(public_pem)
    print(f"✓ Public key saved to {PUBLIC_KEY_PATH}")
    
    return private_pem, public_pem


def setup_well_known_endpoint(public_pem):
    """Set up the .well-known endpoint for Tesla to verify."""
    print(f"\n[*] Setting up .well-known endpoint at {WELL_KNOWN_PUB_KEY}...")
    
    os.makedirs(WELL_KNOWN_DIR, exist_ok=True)
    with open(WELL_KNOWN_PUB_KEY, 'wb') as f:
        f.write(public_pem)
    
    print(f"✓ Public key available at: https://{REDIRECT_HOST}/.well-known/appspecific/com.tesla.3p.public-key.pem")
    return True


def get_partner_token():
    """
    Get partner authentication token.
    
    Note: Partner tokens are different from OAuth access tokens.
    For now, we'll try using the OAuth token.
    """
    print(f"\n[*] Using OAuth access token as bearer token...")
    return TESLA_ACCESS_TOKEN


def register_account(partner_token, public_pem):
    """Register account with Tesla Fleet API."""
    print(f"\n[*] Registering account {TESLA_CLIENT_ID} with Fleet API...")
    
    url = f"{FLEET_API_BASE}/partner_accounts"
    headers = {
        "Authorization": f"Bearer {partner_token}",
        "Content-Type": "application/json",
    }
    
    # Registration payload
    payload = {
        "domain": REDIRECT_HOST,
        "public_key": public_pem.decode('utf-8'),
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Registration successful!")
            return True, response.json()
        else:
            print(f"\n✗ Registration failed: {response.text}")
            return False, response.json()
            
    except Exception as e:
        print(f"\n✗ Error during registration: {e}")
        return False, None


def verify_public_key(partner_token):
    """Verify that the public key was registered."""
    print(f"\n[*] Verifying public key registration...")
    
    url = f"{FLEET_API_BASE}/partner_accounts/public_key"
    headers = {
        "Authorization": f"Bearer {partner_token}",
    }
    params = {
        "domain": REDIRECT_HOST,
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Public key verified!")
            return True, response.json()
        else:
            print(f"\n✗ Verification failed: {response.text}")
            return False, response.json()
            
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        return False, None


def test_vehicles_endpoint(access_token):
    """Test that we can now access the vehicles endpoint."""
    print(f"\n[*] Testing /vehicles endpoint after registration...")
    
    url = f"{FLEET_API_BASE}/vehicles"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Vehicles endpoint is now accessible!")
            return True, response.json()
        else:
            print(f"\n✗ Still getting error: {response.text}")
            return False, response.json()
            
    except Exception as e:
        print(f"\n✗ Error testing endpoint: {e}")
        return False, None


def main():
    print("=" * 60)
    print("Tesla Fleet API Account Registration")
    print("=" * 60)
    
    # Step 1: Generate EC keys
    private_pem, public_pem = generate_ec_keys()
    
    # Step 2: Set up well-known endpoint
    setup_well_known_endpoint(public_pem)
    
    # Step 3: Get partner token
    partner_token = get_partner_token()
    if not partner_token:
        print("\n✗ Failed to get partner token")
        return False
    
    # Step 4: Register account
    success, response = register_account(partner_token, public_pem)
    if not success:
        print("\n✗ Account registration failed. This may require a partner token, not an OAuth token.")
        print("   Please check Tesla documentation for how to obtain a partner token.")
        return False
    
    # Step 5: Verify registration
    success, response = verify_public_key(partner_token)
    if not success:
        print("\n✗ Public key verification failed")
        return False
    
    # Step 6: Test vehicles endpoint
    success, response = test_vehicles_endpoint(TESLA_ACCESS_TOKEN)
    if not success:
        print("\n✗ Vehicles endpoint still not accessible")
        return False
    
    print("\n" + "=" * 60)
    print("✓ Registration complete and verified!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    main()
