"""Pilot gate and admin API for the AI Safety Policy Register.

/login         takes a Clerk session token (from the browser, via getToken()), verifies
               its RS256 signature against Clerk's public JWKS, checks the user's verified
               email against the allowlist, and sets a short-lived HttpOnly cookie signed
               with a local secret.
/verify        is asked by nginx (auth_request) on every request. It checks the cookie and
               re-reads the allowlist, so removing someone takes effect at once.
/admin/api/users  list, add, remove, grant or revoke admin. Admins only.

The Clerk secret key is used only to read a user's email at login.
Verification follows naiid's registry/clerk_auth.py.
"""
import base64
import hashlib
import hmac
import http.cookies
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DOMAIN = os.environ["CLERK_DOMAIN"].strip().lower()
COOKIE_NAME = "register_pilot"
COOKIE_TTL = int(os.environ.get("SESSION_TTL_SECONDS", "28800"))
SECRET_FILE = os.environ.get("COOKIE_SECRET_FILE", "/run/secrets/cookie-secret")
with open(SECRET_FILE, "rb") as fh:
    SECRET = fh.read().strip()
# Clerk secret key: used only to read a user's email at login.
CLERK_SECRET_FILE = os.environ.get("CLERK_SECRET_FILE", "/run/secrets/clerk-secret")
with open(CLERK_SECRET_FILE, "rb") as fh:
    CLERK_SECRET = fh.read().strip().decode("utf-8")

# The config folder is mounted as a directory, so files can be replaced atomically.
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/config")
ALLOWED_NAME = "allowed-emails.txt"
ADMINS_NAME = "admins.txt"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL = 254
_lock = threading.Lock()


def read_list(name):
    path = os.path.join(CONFIG_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [line.strip().lower() for line in fh if line.strip() and not line.lstrip().startswith("#")]


def write_list(name, items):
    """Atomic replace. Keeps the header comment, if any, from the existing file."""
    path = os.path.join(CONFIG_DIR, name)
    header = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            header = [line for line in fh if line.lstrip().startswith("#")]
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.writelines(header)
        for item in sorted(set(items)):
            fh.write(item + "\n")
    os.replace(tmp, path)


GATE_NAME = "pilot-gate.json"


def gate_enabled():
    """False only when an admin has switched the pilot gate off. Missing or unreadable means on."""
    path = os.path.join(CONFIG_DIR, GATE_NAME)
    if not os.path.exists(path):
        return True
    try:
        with open(path, encoding="utf-8") as fh:
            return bool(json.load(fh).get("enabled", True))
    except (ValueError, OSError):
        return True


def write_gate(enabled):
    path = os.path.join(CONFIG_DIR, GATE_NAME)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"enabled": bool(enabled)}, fh)
        fh.write("\n")
    os.replace(tmp, path)


def allowed_emails():
    return set(read_list(ALLOWED_NAME))


def admin_emails():
    return set(read_list(ADMINS_NAME))


def clerk_user_email(sub):
    """Verified email of a Clerk user that is on the allowlist or admin list, or None."""
    req = urllib.request.Request(f"https://api.clerk.com/v1/users/{sub}", headers={
        "Authorization": f"Bearer {CLERK_SECRET}",
        # Same User-Agent naiid uses for the Clerk API.
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) NAIID/1.0",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    permitted = allowed_emails() | admin_emails()
    for addr in data.get("email_addresses", []):
        verified = (addr.get("verification") or {}).get("status") == "verified"
        email = addr.get("email_address", "").lower()
        if verified and email in permitted:
            return email
    return None


JWKS_TTL = 600
_jwks = {"at": 0.0, "keys": []}


def b64d(segment):
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def b64e(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def fetch_jwks():
    url = f"https://{DOMAIN}/.well-known/jwks.json"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8")).get("keys", [])


def find_key(kid):
    now = time.time()
    if now - _jwks["at"] > JWKS_TTL:
        _jwks["keys"] = fetch_jwks()
        _jwks["at"] = now
    key = next((k for k in _jwks["keys"] if k.get("kid") == kid), None)
    if key is None:
        # Clerk rotated its signing key; refresh once.
        _jwks["keys"] = fetch_jwks()
        _jwks["at"] = now
        key = next((k for k in _jwks["keys"] if k.get("kid") == kid), None)
    return key


def verify_rs256(signing_input, signature, n, e):
    """RSASSA-PKCS1-v1_5 with SHA-256 (RFC 8017 section 8.2)."""
    s = int.from_bytes(signature, "big")
    if s >= n:
        return False
    m = pow(s, e, n).to_bytes((n.bit_length() + 7) // 8, "big")
    digest_info = bytes.fromhex("3031300d060960864801650304020105000420") + hashlib.sha256(signing_input).digest()
    expected = b"\x00\x01" + b"\xff" * (len(m) - 3 - len(digest_info)) + b"\x00" + digest_info
    return hmac.compare_digest(m, expected)


def verify_clerk_token(token):
    """Return the claims of a valid Clerk session token, or None."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(b64d(header_b64))
        claims = json.loads(b64d(payload_b64))
        signature = b64d(sig_b64)
    except (ValueError, json.JSONDecodeError):
        return None
    if header.get("alg") != "RS256":
        return None
    jwk = find_key(header.get("kid"))
    if jwk is None:
        return None
    n = int.from_bytes(b64d(jwk["n"]), "big")
    e = int.from_bytes(b64d(jwk["e"]), "big")
    if not verify_rs256(f"{header_b64}.{payload_b64}".encode("ascii"), signature, n, e):
        return None
    now = time.time()
    if claims.get("iss") != f"https://{DOMAIN}":
        return None
    # Clerk session tokens do not always carry "aud" (same finding as naiid).
    if claims.get("aud") is not None and claims.get("aud") != DOMAIN:
        return None
    if int(claims.get("exp", 0)) < now or int(claims.get("nbf", 0)) > now:
        return None
    return claims


def make_cookie_value(sub, email):
    payload = b64e(json.dumps({"sub": sub, "email": email, "exp": int(time.time()) + COOKIE_TTL}).encode("utf-8"))
    mac = b64e(hmac.new(SECRET, payload.encode("ascii"), hashlib.sha256).digest())
    return f"{payload}.{mac}"


def cookie_data(value):
    """The signed cookie's payload, or None if it is forged, expired or has no email."""
    try:
        payload, mac = value.split(".")
    except ValueError:
        return None
    expected = b64e(hmac.new(SECRET, payload.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(mac, expected):
        return None
    try:
        data = json.loads(b64d(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(data.get("exp", 0)) <= time.time() or not data.get("email"):
        return None
    return data


def current_user(headers):
    """Email from a valid cookie, if that email is still on the allowlist or admin list now."""
    jar = http.cookies.SimpleCookie(headers.get("Cookie", ""))
    morsel = jar.get(COOKIE_NAME)
    if morsel is None:
        return None
    data = cookie_data(morsel.value)
    if data is None:
        return None
    email = data["email"]
    return email if email in (allowed_emails() | admin_emails()) else None


class Handler(BaseHTTPRequestHandler):
    server_version = "register-auth"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def _send(self, status, headers=None):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = min(int(self.headers.get("Content-Length", "0") or 0), 4096)
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _listing(self, me):
        return {"you": me, "allowed": sorted(allowed_emails()), "admins": sorted(admin_emails()),
                "gate_enabled": gate_enabled()}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/logout":
            # Clear the pilot cookie, then land on the sign-in page, which also signs out of Clerk.
            clear = f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
            return self._send(302, {"Set-Cookie": clear, "Location": "/sign-in/?signed_out=1"})
        if path == "/gate":
            # Public: lets the viewer hide Pilot logout while the gate is off. Reveals only on/off.
            return self._send_json(200, {"enabled": gate_enabled()})
        if path == "/verify":
            if not gate_enabled():
                return self._send(204)
            return self._send(204 if current_user(self.headers) else 401)
        if path == "/admin/api/users":
            me = current_user(self.headers)
            if me is None:
                return self._send_json(401, {"error": "Not signed in."})
            if me not in admin_emails():
                return self._send_json(403, {"error": "Admins only."})
            return self._send_json(200, self._listing(me))
        return self._send(404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/login":
            return self._login()
        if path == "/admin/api/users":
            return self._admin_change()
        return self._send(404)

    def _login(self):
        try:
            token = self._read_json().get("token", "")
        except (ValueError, json.JSONDecodeError):
            return self._send(400)
        try:
            claims = verify_clerk_token(token) if isinstance(token, str) and token else None
        except Exception:
            # Usually Clerk's JWKS unreachable or TLS trust failing; never crash the server.
            sys.stderr.write("token check failed\n")
            traceback.print_exc()
            return self._send(503)
        if claims is None:
            return self._send(401)
        try:
            email = clerk_user_email(claims.get("sub"))
        except Exception:
            sys.stderr.write("allowlist check failed\n")
            traceback.print_exc()
            return self._send(503)
        if email is None:
            sys.stderr.write("login refused sub=%s\n" % claims.get("sub"))
            return self._send(403)
        sys.stderr.write("login sub=%s\n" % claims.get("sub"))
        cookie = f"{COOKIE_NAME}={make_cookie_value(claims.get('sub'), email)}; Path=/; Max-Age={COOKIE_TTL}; HttpOnly; SameSite=Lax"
        self._send(204, {"Set-Cookie": cookie})

    def _admin_change(self):
        me = current_user(self.headers)
        if me is None:
            return self._send_json(401, {"error": "Not signed in."})
        if me not in admin_emails():
            return self._send_json(403, {"error": "Admins only."})
        try:
            body = self._read_json()
        except (ValueError, json.JSONDecodeError):
            return self._send_json(400, {"error": "Bad request."})
        action = body.get("action")
        if action in ("gate_on", "gate_off"):
            with _lock:
                write_gate(action == "gate_on")
            sys.stderr.write("admin %s %s\n" % (me, action))
            return self._send_json(200, self._listing(me))
        email = str(body.get("email", "")).strip().lower()
        if action not in ("add", "remove", "grant", "revoke"):
            return self._send_json(400, {"error": "Unknown action."})
        if len(email) > MAX_EMAIL or not EMAIL_RE.match(email):
            return self._send_json(400, {"error": "Enter a valid email address."})

        with _lock:
            allowed = allowed_emails()
            admins = admin_emails()
            if action == "add":
                allowed.add(email)
            elif action == "grant":
                allowed.add(email)
                admins.add(email)
            elif action == "revoke":
                if email == me:
                    return self._send_json(409, {"error": "You cannot remove your own admin rights."})
                if email in admins and len(admins) == 1:
                    return self._send_json(409, {"error": "At least one admin must remain."})
                admins.discard(email)
            elif action == "remove":
                if email == me:
                    return self._send_json(409, {"error": "You cannot remove your own access."})
                if email in admins and len(admins) == 1:
                    return self._send_json(409, {"error": "At least one admin must remain."})
                allowed.discard(email)
                admins.discard(email)
            write_list(ALLOWED_NAME, allowed)
            write_list(ADMINS_NAME, admins)
        sys.stderr.write("admin %s %s %s\n" % (me, action, email))
        return self._send_json(200, self._listing(me))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
