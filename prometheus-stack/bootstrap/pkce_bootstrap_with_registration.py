#!/usr/bin/env python3
"""
Register with Tesla Fleet API and host public key.

This enhanced bootstrap script:
1. Runs PKCE OAuth flow to get tokens
2. Generates an EC public key (secp256r1 curve)
3. Hosts the key at .well-known/appspecific/com.tesla.3p.public-key.pem
4. Registers the account with Tesla Fleet API
5. Continues to serve the public key for Tesla to verify
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from pathlib import Path

import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography library not available.", flush=True)


# Config from environment
TESLA_CLIENT_ID = os.getenv("TESLA_CLIENT_ID")
TESLA_CLIENT_SECRET = os.getenv("TESLA_CLIENT_SECRET")
TESLA_AUTH_URL = os.getenv("TESLA_AUTH_URL", "https://auth.tesla.com/oauth2/v3/authorize")
TESLA_TOKEN_URL = os.getenv("TESLA_TOKEN_URL", "https://auth.tesla.com/oauth2/v3/token")
REDIRECT_HOST = os.getenv("REDIRECT_HOST", "sentiently-thigmotactic-desirae.ngrok-free.dev")
REDIRECT_PORT = int(os.getenv("REDIRECT_PORT", "8080"))
TESLA_SECRET_NAME = os.getenv("TESLA_SECRET_NAME", "tesla-credentials")
NAMESPACE = os.getenv("NAMESPACE", "default")
SCOPE = os.getenv("SCOPE", "openid email offline_access vehicle_device_data")
FLEET_API_BASE = "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1"

# Key storage
BOOTSTRAP_HOST_PATH = Path("/bootstrap_host")
EC_PRIVATE_KEY_FILE = BOOTSTRAP_HOST_PATH / "tesla_ec_private_key.pem"
EC_PUBLIC_KEY_FILE = BOOTSTRAP_HOST_PATH / "tesla_ec_public_key.pem"
WELL_KNOWN_DIR = Path("/app/.well-known/appspecific")
WELL_KNOWN_PUB_KEY = WELL_KNOWN_DIR / "com.tesla.3p.public-key.pem"

# Track state
auth_code = None
auth_error = None
tokens = {}
registration_complete = False


class PKCECallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback."""
    
    def do_GET(self):
        global auth_code, auth_error
        
        if self.path.startswith("/.well-known/"):
            # Serve public key
            self.serve_public_key()
        elif self.path.startswith("/callback"):
            # Handle OAuth callback
            self.handle_oauth_callback()
        else:
            self.send_response(404)
            self.end_headers()
    
    def serve_public_key(self):
        """Serve the public key at .well-known path."""
        try:
            if WELL_KNOWN_PUB_KEY.exists():
                with open(WELL_KNOWN_PUB_KEY, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-pem-file')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
                print(f"[+] Served public key to {self.client_address[0]}", flush=True)
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Public key not ready yet")
        except Exception as e:
            print(f"ERROR serving public key: {e}", flush=True)
            self.send_response(500)
            self.end_headers()
    
    def handle_oauth_callback(self):
        """Handle OAuth callback with code."""
        global auth_code, auth_error
        
        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        if 'error' in query_params:
            auth_error = query_params['error'][0]
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Authorization error: {auth_error}".encode())
            print(f"[!] Authorization error: {auth_error}", flush=True)
        elif 'code' in query_params:
            auth_code = query_params['code'][0]
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>Authorization Successful!</h1>
            <p>You can close this window.</p>
            <p>The application is registering with Tesla Fleet API...</p>
            </body>
            </html>
            """)
            print(f"[+] Received authorization code", flush=True)
        else:
            self.send_response(400)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Missing authorization code")
            print(f"[!] Missing authorization code in callback", flush=True)
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def generate_ec_keys():
    """Generate EC key pair with secp256r1 curve."""
    print("[*] Generating EC key pair (secp256r1 curve)...", flush=True)
    
    if not CRYPTO_AVAILABLE:
        print("[!] cryptography library not available, skipping EC key generation", flush=True)
        return None, None
    
    try:
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
        
        # Save keys to bootstrap_host mount
        BOOTSTRAP_HOST_PATH.mkdir(parents=True, exist_ok=True)
        with open(EC_PRIVATE_KEY_FILE, 'wb') as f:
            f.write(private_pem)
        with open(EC_PUBLIC_KEY_FILE, 'wb') as f:
            f.write(public_pem)
        print(f"[+] EC keys generated and saved", flush=True)
        
        # Also save to .well-known for serving
        WELL_KNOWN_DIR.mkdir(parents=True, exist_ok=True)
        with open(WELL_KNOWN_PUB_KEY, 'wb') as f:
            f.write(public_pem)
        print(f"[+] Public key available at: https://{REDIRECT_HOST}/.well-known/appspecific/com.tesla.3p.public-key.pem", flush=True)
        
        return private_pem, public_pem
    except Exception as e:
        print(f"[!] Error generating EC keys: {e}", flush=True)
        return None, None


def generate_pkce():
    """Generate PKCE code_verifier and code_challenge."""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


def get_authorization_url(code_challenge):
    """Generate the authorization URL."""
    params = {
        'client_id': TESLA_CLIENT_ID,
        'redirect_uri': f'https://{REDIRECT_HOST}/callback',
        'response_type': 'code',
        'scope': SCOPE,
        'state': secrets.token_urlsafe(16),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    return f"{TESLA_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code, code_verifier):
    """Exchange authorization code for tokens."""
    print("[*] Exchanging code for tokens...", flush=True)
    
    payload = {
        'grant_type': 'authorization_code',
        'client_id': TESLA_CLIENT_ID,
        'client_secret': TESLA_CLIENT_SECRET,
        'code': code,
        'redirect_uri': f'https://{REDIRECT_HOST}/callback',
        'code_verifier': code_verifier,
    }
    
    try:
        response = requests.post(TESLA_TOKEN_URL, data=payload, timeout=30)
        response.raise_for_status()
        
        global tokens
        tokens = response.json()
        print(f"[+] Tokens received (expires in {tokens.get('expires_in')} seconds)", flush=True)
        return tokens
    except Exception as e:
        print(f"[!] Error exchanging code: {e}", flush=True)
        return None


def get_partner_token():
    """Get partner authentication token using client credentials flow."""
    print("[*] Getting partner token using client credentials...", flush=True)
    
    token_url = "https://fleet-auth.prd.vn.cloud.tesla.com/oauth2/v3/token"
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': TESLA_CLIENT_ID,
        'client_secret': TESLA_CLIENT_SECRET,
        'audience': 'https://fleet-api.prd.na.vn.cloud.tesla.com',
        'scope': 'openid vehicle_device_data vehicle_cmds vehicle_charging_cmds',
    }
    
    try:
        response = requests.post(token_url, data=payload, timeout=30)
        response.raise_for_status()
        
        token_data = response.json()
        partner_token = token_data.get('access_token')
        print(f"[+] Partner token received (expires in {token_data.get('expires_in')} seconds)", flush=True)
        return partner_token
    except Exception as e:
        print(f"[!] Error getting partner token: {e}", flush=True)
        return None


def register_with_fleet_api(partner_token, public_key_pem):
    """Register account with Tesla Fleet API using partner token."""
    global registration_complete
    
    print("[*] Registering with Tesla Fleet API...", flush=True)
    
    if not public_key_pem:
        print("[!] No public key available for registration", flush=True)
        return False
    
    if not partner_token:
        print("[!] No partner token available for registration", flush=True)
        return False
    
    url = f"{FLEET_API_BASE}/partner_accounts"
    headers = {
        "Authorization": f"Bearer {partner_token}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "domain": REDIRECT_HOST,
        "public_key": public_key_pem.decode('utf-8') if isinstance(public_key_pem, bytes) else public_key_pem,
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"    Status: {response.status_code}", flush=True)
        print(f"    Body: {response.text}", flush=True)
        
        if response.status_code in (200, 201):
            print(f"[+] Registration successful!", flush=True)
            registration_complete = True
            return True
        else:
            print(f"[!] Registration failed: {response.text}", flush=True)
            return False
    except Exception as e:
        print(f"[!] Error registering: {e}", flush=True)
        return False


def verify_public_key(partner_token):
    """Verify public key was registered using partner token."""
    print("[*] Verifying public key registration...", flush=True)
    
    if not partner_token:
        print("[!] No partner token available for verification", flush=True)
        return False
    
    url = f"{FLEET_API_BASE}/partner_accounts/public_key"
    headers = {
        "Authorization": f"Bearer {partner_token}",
    }
    params = {"domain": REDIRECT_HOST}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"    Status: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            print(f"[+] Public key verified!", flush=True)
            return True
        else:
            print(f"[!] Verification failed: {response.text}", flush=True)
            return False
    except Exception as e:
        print(f"[!] Error verifying: {e}", flush=True)
        return False


def save_tokens_to_file(tokens_dict):
    """Save tokens to .env file."""
    env_file = BOOTSTRAP_HOST_PATH / ".env"
    
    try:
        content = f"""TESLA_ACCESS_TOKEN={tokens_dict.get('access_token')}
TESLA_REFRESH_TOKEN={tokens_dict.get('refresh_token')}
TESLA_ID_TOKEN={tokens_dict.get('id_token')}
TESLA_TOKEN_EXPIRES_IN={tokens_dict.get('expires_in')}
TESLA_TOKEN_EXPIRES_AT={datetime.now().timestamp() + tokens_dict.get('expires_in', 3600)}
TESLA_CLIENT_ID={TESLA_CLIENT_ID}
TESLA_CLIENT_SECRET={TESLA_CLIENT_SECRET}
"""
        with open(env_file, 'a') as f:
            f.write(content)
        print(f"[+] Tokens saved to {env_file}", flush=True)
    except Exception as e:
        print(f"[!] Error saving tokens: {e}", flush=True)


def start_server():
    """Start HTTP server."""
    server = HTTPServer(('0.0.0.0', REDIRECT_PORT), PKCECallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[+] Server listening on port {REDIRECT_PORT}", flush=True)
    return server


def main():
    print("=" * 60, flush=True)
    print("Tesla Fleet API Bootstrap + Registration", flush=True)
    print("=" * 60, flush=True)
    
    # Step 1: Generate EC keys
    private_pem, public_pem = generate_ec_keys()
    
    # Step 2: Start HTTP server
    server = start_server()
    
    # Step 3: Generate PKCE
    print("[*] Generating PKCE parameters...", flush=True)
    code_verifier, code_challenge = generate_pkce()
    
    # Step 4: Get authorization URL
    auth_url = get_authorization_url(code_challenge)
    print(f"\n[!] Please visit this URL to authorize:\n\n{auth_url}\n", flush=True)
    
    # Step 5: Wait for callback
    print("[*] Waiting for authorization callback...", flush=True)
    import time
    while auth_code is None and auth_error is None:
        time.sleep(1)
    
    if auth_error:
        print(f"[!] Authorization failed: {auth_error}", flush=True)
        return False
    
    # Step 6: Exchange code for tokens
    tokens_dict = exchange_code_for_tokens(auth_code, code_verifier)
    if not tokens_dict:
        print("[!] Failed to get tokens", flush=True)
        return False
    
    # Step 7: Save tokens
    save_tokens_to_file(tokens_dict)
    
    # Step 8: Get partner token
    partner_token = get_partner_token()
    if not partner_token:
        print("[!] Failed to get partner token", flush=True)
        return False
    
    # Step 9: Register with Fleet API using partner token
    if not register_with_fleet_api(partner_token, public_pem):
        print("[!] Registration failed", flush=True)
    
    # Step 10: Verify registration using partner token
    verify_public_key(partner_token)
    
    # Step 11: Keep server running
    print("\n[*] Bootstrap complete. Keeping server running to serve public key...", flush=True)
    print(f"[+] Public key endpoint: https://{REDIRECT_HOST}/.well-known/appspecific/com.tesla.3p.public-key.pem", flush=True)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down...", flush=True)
        server.shutdown()
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
