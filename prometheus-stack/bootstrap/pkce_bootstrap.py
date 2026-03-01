"""PKCE bootstrap helper.

Behavior:
- Generates PKCE code_verifier/code_challenge
- Prints an authorization URL to stdout (open it in your browser)
- Starts a local HTTP server to receive the authorization callback
- Exchanges the code for tokens
- Writes/patches a Kubernetes Secret named by `TESLA_SECRET_NAME` in the namespace

Environment variables (in-cluster Job should set these):
- TESLA_CLIENT_ID (required)
- TESLA_AUTH_URL (optional)
- TESLA_TOKEN_URL (optional)
- REDIRECT_PORT (optional, default 8080)
- TESLA_SECRET_NAME (optional, default tesla-credentials)
- NAMESPACE (optional, default: from serviceaccount file or 'default')

Note: The Job's ServiceAccount must have permission to create/update the Secret.
"""

import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta

import requests
from kubernetes import client, config
from kubernetes.client.rest import ApiException

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("WARNING: cryptography library not available. Certificate generation will be skipped.", flush=True)


TESLA_CLIENT_ID = os.getenv("TESLA_CLIENT_ID")
TESLA_CLIENT_SECRET = os.getenv("TESLA_CLIENT_SECRET")
TESLA_AUTH_URL = os.getenv("TESLA_AUTH_URL", "https://auth.tesla.com/oauth2/v3/authorize")
TESLA_TOKEN_URL = os.getenv("TESLA_TOKEN_URL", "https://auth.tesla.com/oauth2/v3/token")
REDIRECT_PORT = int(os.getenv("REDIRECT_PORT", "8080"))
TESLA_SECRET_NAME = os.getenv("TESLA_SECRET_NAME", "tesla-credentials")
NAMESPACE = os.getenv("NAMESPACE")
SCOPE = os.getenv("SCOPE", "openid email offline_access vehicle_device_data")

if not TESLA_CLIENT_ID:
    raise SystemExit("TESLA_CLIENT_ID environment variable is required for PKCE flow")


def b64url_encode(inp: bytes) -> str:
    return base64.urlsafe_b64encode(inp).rstrip(b"=").decode("ascii")


code_verifier = b64url_encode(secrets.token_bytes(40))
code_challenge = b64url_encode(hashlib.sha256(code_verifier.encode("ascii")).digest())

# Use an externally reachable redirect host by default when running locally.
# For in-cluster runs you can set REDIRECT_HOST to the node IP or expose the pod.
REDIRECT_HOST = os.getenv("REDIRECT_HOST", "localhost")

# Detect if using ngrok tunnel (which requires https and no port in the URI)
if ".ngrok" in REDIRECT_HOST:
    redirect_uri = f"https://{REDIRECT_HOST}/callback"
else:
    redirect_uri = f"http://{REDIRECT_HOST}:{REDIRECT_PORT}/callback"

query = {
    "client_id": TESLA_CLIENT_ID,
    "redirect_uri": redirect_uri,
    "response_type": "code",
    "scope": SCOPE,
    "code_challenge": code_challenge,
    "code_challenge_method": "S256",
}

auth_url = TESLA_AUTH_URL + "?" + urllib.parse.urlencode(query)

print("Open the following URL in your browser to authorize this application:\n")
print(auth_url)
print("\nAfter you allow access the browser will redirect to this Job and the token will be written into the cluster Secret.")


def generate_certificate():
    """Generate a self-signed X.509 certificate for Tesla Fleet API."""
    if not CRYPTO_AVAILABLE:
        print("Skipping certificate generation: cryptography library not available", flush=True)
        return None, None
    
    try:
        print("Generating self-signed certificate for Tesla Fleet API...", flush=True)
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Build certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Palo Alto"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Tesla Collector"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"tesla-collector"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"tesla-collector"),
                x509.DNSName(u"localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Serialize to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        
        print("Certificate generated successfully", flush=True)
        return private_pem.decode(), cert_pem.decode()
    except Exception as e:
        print(f"ERROR generating certificate: {e}", flush=True)
        return None, None


class CallbackHandler(BaseHTTPRequestHandler):
    server_version = "PKCEBootstrap/0.1"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code parameter")
            return

        # Exchange code for token
        try:
            payload = {
                "grant_type": "authorization_code",
                "client_id": TESLA_CLIENT_ID,
                "client_secret": TESLA_CLIENT_SECRET,
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": redirect_uri,
            }
            print(f"Token request payload: grant_type={payload['grant_type']}, client_id={payload['client_id']}, code_verifier={payload['code_verifier']}, redirect_uri={payload['redirect_uri']}", flush=True)
            token_resp = requests.post(
                TESLA_TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            print(f"Token response status: {token_resp.status_code}", flush=True)
            print(f"Token response body: {token_resp.text}", flush=True)
            token_resp.raise_for_status()
            token_data = token_resp.json()
        except requests.exceptions.HTTPError as e:
            self.send_response(500)
            self.end_headers()
            msg = f"Token exchange HTTP error: {e}\nStatus: {token_resp.status_code}\nResponse: {token_resp.text}\n"
            self.wfile.write(msg.encode("utf-8"))
            print(msg, flush=True)
            return
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            msg = f"Token exchange failed: {e}\n"
            self.wfile.write(msg.encode("utf-8"))
            print(msg, flush=True)
            return

        # Write secret to Kubernetes or fallback to .env file
        try:
            # Determine namespace
            ns = NAMESPACE
            if not ns:
                try:
                    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as fh:
                        ns = fh.read().strip()
                except Exception:
                    ns = "default"

            # Prefer in-cluster config, but fall back to local kubeconfig for running
            # this script on your workstation (so you can receive the callback locally
            # and have the script write the Secret into the cluster).
            try:
                config.load_incluster_config()
            except Exception:
                config.load_kube_config()

            v1 = client.CoreV1Api()

            string_data = {
                "access_token": token_data.get("access_token", ""),
                "refresh_token": token_data.get("refresh_token", ""),
                "id_token": token_data.get("id_token", ""),
            }

            metadata = client.V1ObjectMeta(name=TESLA_SECRET_NAME)
            body = client.V1Secret(metadata=metadata, string_data=string_data)

            try:
                v1.create_namespaced_secret(namespace=ns, body=body)
                print(f"Created secret {TESLA_SECRET_NAME} in namespace {ns}", flush=True)
            except ApiException as exc:
                if exc.status == 409:
                    # Already exists -> patch
                    v1.patch_namespaced_secret(name=TESLA_SECRET_NAME, namespace=ns, body=body)
                    print(f"Patched secret {TESLA_SECRET_NAME} in namespace {ns}", flush=True)
                else:
                    raise

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization successful. Token written to Kubernetes Secret. You can close this window.")
            print("Wrote token to Kubernetes Secret; exiting server.", flush=True)
            
            # stop server in a separate thread
            threading.Thread(target=self.server.shutdown).start()
        except Exception as e:
            # Fallback: write tokens to .env file for local testing
            print(f"Kubernetes write failed ({e}), writing to .env file instead...", flush=True)
            try:
                # Generate certificate
                private_key_pem, cert_pem = generate_certificate()
                
                env_content = f"""TESLA_ACCESS_TOKEN={token_data.get("access_token", "")}
TESLA_REFRESH_TOKEN={token_data.get("refresh_token", "")}
TESLA_ID_TOKEN={token_data.get("id_token", "")}
"""
                # Write to mounted volume host at /bootstrap_host/.env
                with open("/bootstrap_host/.env", "a") as f:
                    f.write(env_content)
                print(f"Wrote tokens to /bootstrap_host/.env", flush=True)
                
                # Save certificate files if generated
                if private_key_pem and cert_pem:
                    with open("/bootstrap_host/tesla_private_key.pem", "w") as f:
                        f.write(private_key_pem)
                    with open("/bootstrap_host/tesla_certificate.pem", "w") as f:
                        f.write(cert_pem)
                    print("Saved certificate files: tesla_private_key.pem, tesla_certificate.pem", flush=True)
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization successful. Token written to .env file. You can close this window.")
                print(f"Wrote tokens to /app/.env", flush=True)
                
                # stop server in a separate thread
                threading.Thread(target=self.server.shutdown).start()
            except Exception as env_err:
                self.send_response(500)
                self.end_headers()
                msg = f"Failed writing to both Kubernetes and .env: {env_err}\n"
                self.wfile.write(msg.encode("utf-8"))
                print(msg, flush=True)
                return


def run_server():
    server = HTTPServer(("0.0.0.0", REDIRECT_PORT), CallbackHandler)
    print(f"Listening for callback on port {REDIRECT_PORT}...")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
