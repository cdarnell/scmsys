"""OAuth2 / PKCE helpers.

This module provides token management functions:

- `get_access_token()`: Return the current access token from env var or refresh if expired
- `refresh_access_token()`: Use refresh_token to get a new access_token
- For quick connectivity tests, set TESLA_ACCESS_TOKEN in your .env

For production, the bootstrap script handles PKCE and stores tokens to .env.
"""

import os
import json
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


TESLA_CLIENT_ID = os.getenv("TESLA_CLIENT_ID")
TESLA_CLIENT_SECRET = os.getenv("TESLA_CLIENT_SECRET")
TESLA_TOKEN_URL = os.getenv("TESLA_TOKEN_URL", "https://auth.tesla.com/oauth2/v3/token")


def _load_tokens() -> Dict[str, str]:
    """Load tokens from environment variables."""
    return {
        "access_token": os.getenv("TESLA_ACCESS_TOKEN", ""),
        "refresh_token": os.getenv("TESLA_REFRESH_TOKEN", ""),
        "id_token": os.getenv("TESLA_ID_TOKEN", ""),
        "token_type": os.getenv("TESLA_TOKEN_TYPE", "Bearer"),
    }


def _save_tokens(tokens: Dict[str, str]) -> None:
    """Save tokens to .env file."""
    env_file = ".env"
    if os.path.exists(env_file):
        # Read existing .env
        with open(env_file, "r") as f:
            lines = f.readlines()
        
        # Update token lines
        token_keys = {"TESLA_ACCESS_TOKEN", "TESLA_REFRESH_TOKEN", "TESLA_ID_TOKEN", "TESLA_TOKEN_TYPE"}
        updated_lines = [l for l in lines if not any(l.startswith(k) for k in token_keys)]
        
        # Add new token lines
        updated_lines.extend([
            f"TESLA_ACCESS_TOKEN={tokens.get('access_token', '')}\n",
            f"TESLA_REFRESH_TOKEN={tokens.get('refresh_token', '')}\n",
            f"TESLA_ID_TOKEN={tokens.get('id_token', '')}\n",
            f"TESLA_TOKEN_TYPE={tokens.get('token_type', 'Bearer')}\n",
        ])
        
        with open(env_file, "w") as f:
            f.writelines(updated_lines)


def is_token_expired(token: str) -> bool:
    """Check if a JWT token is expired by decoding the payload."""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return True
        
        # Decode payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        import base64
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        # Check expiration
        exp = payload_data.get("exp", 0)
        return datetime.fromtimestamp(exp) < datetime.now()
    except Exception:
        return True


def refresh_access_token() -> bool:
    """Refresh the access token using the refresh_token.
    
    Returns True if successful, False otherwise.
    """
    tokens = _load_tokens()
    refresh_token = tokens.get("refresh_token")
    
    if not refresh_token:
        print("No refresh_token available")
        return False
    
    try:
        resp = requests.post(
            TESLA_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": TESLA_CLIENT_ID,
                "client_secret": TESLA_CLIENT_SECRET,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        resp.raise_for_status()
        token_data = resp.json()
        
        # Update tokens in memory and on disk
        new_tokens = {
            "access_token": token_data.get("access_token", ""),
            "refresh_token": token_data.get("refresh_token", refresh_token),  # Keep old if not provided
            "id_token": token_data.get("id_token", ""),
            "token_type": token_data.get("token_type", "Bearer"),
        }
        
        # Update environment and .env file
        os.environ["TESLA_ACCESS_TOKEN"] = new_tokens["access_token"]
        os.environ["TESLA_REFRESH_TOKEN"] = new_tokens["refresh_token"]
        os.environ["TESLA_ID_TOKEN"] = new_tokens["id_token"]
        os.environ["TESLA_TOKEN_TYPE"] = new_tokens["token_type"]
        
        _save_tokens(new_tokens)
        print(f"Successfully refreshed access token (expires in {token_data.get('expires_in', 'unknown')}s)")
        return True
    except Exception as e:
        print(f"Failed to refresh token: {e}")
        return False


def get_access_token() -> str:
    """Return a valid access token, refreshing if needed.

    Returns the value of TESLA_ACCESS_TOKEN env var if valid.
    If expired, attempts to refresh using refresh_token.
    Raises NotImplementedError if no token is available.
    """
    token: Optional[str] = os.getenv("TESLA_ACCESS_TOKEN")
    if not token:
        raise NotImplementedError(
            "No TESLA_ACCESS_TOKEN found in environment. Implement OAuth2 PKCE flow or set TESLA_ACCESS_TOKEN."
        )
    
    # Check if token is expired
    if is_token_expired(token):
        print("Access token expired, attempting to refresh...")
        if refresh_access_token():
            return os.getenv("TESLA_ACCESS_TOKEN", token)
        else:
            print("Token refresh failed, returning expired token (API call may still fail)")
    
    return token
