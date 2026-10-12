"""Mint a pilot cookie for testing. Reads COOKIE_SECRET from deploy/pilot-gate/local/.env.

Usage: python3 mint_cookie.py EMAIL [SUB]   -> prints "register_pilot=..."
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(HERE, "..", "local", ".env")


def read_env(path):
    values = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.rstrip("\n").split("=", 1)
                values[key.strip()] = value.strip()
    return values


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


if __name__ == "__main__":
    env = read_env(ENV_FILE)
    email = sys.argv[1]
    sub = sys.argv[2] if len(sys.argv) > 2 else "test-user"
    ttl = int(env.get("SESSION_TTL_SECONDS", "28800"))
    payload = b64(json.dumps({"sub": sub, "email": email, "exp": int(time.time()) + ttl}).encode("utf-8"))
    mac = b64(hmac.new(env["COOKIE_SECRET"].encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest())
    print(f"register_pilot={payload}.{mac}")
