import os
import requests
from typing import Any, Dict
from .auth import get_access_token


class TeslaClient:
    """Minimal Tesla API client for Fleet API."""

    def __init__(self):
        # Get token on demand (will auto-refresh if expired)
        self.access_token = get_access_token()
        # Use Fleet API endpoint instead of legacy Owner API
        self.base = "https://fleet-api.prd.na.vn.cloud.tesla.com/api/1"
        
        # Get certificate paths (optional, for Fleet API registration)
        self.cert_path = os.getenv("TESLA_CERT_PATH", "tesla_certificate.pem")
        self.key_path = os.getenv("TESLA_KEY_PATH", "tesla_private_key.pem")

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}", "Accept": "application/json"}
    
    def _get_cert_tuple(self) -> Any:
        """Return certificate tuple for requests if files exist."""
        cert_exists = os.path.exists(self.cert_path)
        key_exists = os.path.exists(self.key_path)
        
        if cert_exists and key_exists:
            return (self.cert_path, self.key_path)
        return None

    def get_vehicles(self) -> Any:
        url = f"{self.base}/vehicles"
        cert = self._get_cert_tuple()
        resp = requests.get(url, headers=self._headers(), cert=cert, timeout=10)
        resp.raise_for_status()
        return resp.json()