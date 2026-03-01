import os
import sys
import json
from config import Settings
from api.auth import get_access_token
from api.client import TeslaClient


def main():
    settings = Settings()
    try:
        token = get_access_token()
    except NotImplementedError as e:
        print("ERROR: no access token available:", e)
        sys.exit(2)

    client = TeslaClient()
    try:
        resp = client.get_vehicles()
        print(json.dumps(resp, indent=2))
        print("SUCCESS: fetched vehicle data")
    except Exception as exc:
        print("ERROR: failed to fetch vehicles:", exc)
        sys.exit(1)


if __name__ == '__main__':
    main()
