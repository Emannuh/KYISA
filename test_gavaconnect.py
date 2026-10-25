"""
GavaConnect KRA TC001 - Local Test Script
=========================================
Usage:
    python test_gavaconnect.py [kra_pin]

    kra_pin defaults to the sandbox test PIN A011124346B.

Credentials are loaded from .env (never hardcoded here).
Create a .env file in the project root with these keys:

    GAVACONNECT_CLIENT_ID=your_consumer_key
    GAVACONNECT_CLIENT_SECRET=your_consumer_secret
    GAVACONNECT_ENVIRONMENT=sandbox
"""

import sys
import os
import base64
import warnings

import requests

warnings.filterwarnings("ignore")  # suppress SSL warnings for expired certs

# ---------------------------------------------------------------------------
# Load .env manually (no dotenv dependency required)
# ---------------------------------------------------------------------------
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

CLIENT_ID     = os.environ.get("GAVACONNECT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GAVACONNECT_CLIENT_SECRET", "")
ENVIRONMENT   = os.environ.get("GAVACONNECT_ENVIRONMENT", "sandbox")

if not CLIENT_ID or not CLIENT_SECRET:
    print("ERROR: GAVACONNECT_CLIENT_ID and GAVACONNECT_CLIENT_SECRET must be set in .env")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Gateway base URLs
# ---------------------------------------------------------------------------
if ENVIRONMENT == "production":
    BASE = "https://api.kra.go.ke"
else:
    BASE = "https://sbx.kra.go.ke"

# ---------------------------------------------------------------------------
# Token endpoint candidates (probed in order, both GET and POST)
# Stop probing once an access_token is found.
# TODO: replace with the confirmed path from the developer portal app page.
# ---------------------------------------------------------------------------
TOKEN_PATHS = [
    "/v1/token/generate?grant_type=client_credentials",
    "/token/generate?grant_type=client_credentials",
    "/oauth/client_credential/accesstoken?grant_type=client_credentials",
    "/oauth/token",
    "/oauth2/token",
    "/token",
]

# ---------------------------------------------------------------------------
# TC001 obligation endpoint
# TODO: paste the exact path from your app's API docs on developer.go.ke
# ---------------------------------------------------------------------------
OBLIGATION_PATH = "/dtd/checker/v1/obligation"

# ---------------------------------------------------------------------------
# PIN to test with
# ---------------------------------------------------------------------------
TEST_PIN = sys.argv[1] if len(sys.argv) > 1 else "A011124346B"

# Known sandbox test PINs to try if the default fails
SANDBOX_TEST_PINS = [
    "A011124346B",  # shown on portal
    "P051234567A",  # common KRA sandbox test PIN
    "A001234567B",
    "P000000001A",
]

TIMEOUT = 15


def is_html(text):
    """Return True if the response body looks like an HTML page."""
    return text.lstrip().startswith(("<", "<!"))


def interpret(status, text, method, url):
    """Print a short interpretation of the response."""
    if is_html(text):
        print(f"  Interpretation: HTML page returned - wrong host or path")
        return
    if status == 200:
        print(f"  Interpretation: non-HTML 200 - likely correct path")
    elif status in (401, 403):
        print(f"  Interpretation: non-HTML {status} - path exists, credentials or scope issue")
    elif status in (404, 405):
        print(f"  Interpretation: non-HTML {status} - wrong path or method")
    else:
        print(f"  Interpretation: non-HTML {status}")


def try_token(url, method, headers, data):
    """Attempt one token request. Return token string or None."""
    try:
        if method == "POST":
            r = requests.post(url, headers=headers, data=data, timeout=TIMEOUT, verify=False)
        else:
            r = requests.get(url, headers=headers, params=data, timeout=TIMEOUT, verify=False)

        body_preview = r.text[:200]
        print(f"  {method} {url}")
        print(f"  Status : {r.status_code}")
        print(f"  Body   : {body_preview}")
        interpret(r.status_code, r.text, method, url)

        if r.status_code == 200 and not is_html(r.text):
            try:
                token = r.json().get("access_token", "")
                if token:
                    return token
            except Exception:
                pass
    except requests.exceptions.ConnectionError as e:
        print(f"  {method} {url}")
        print(f"  Connection error: {e}")
        print(f"  Interpretation: host unreachable or DNS failure")
    except Exception as e:
        print(f"  {method} {url}")
        print(f"  Error: {e}")
    return None


def get_token():
    """Probe token endpoint candidates and return the first token found."""
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    print(f"\nBase URL   : {BASE}")
    print(f"Environment: {ENVIRONMENT}")
    print(f"Probing {len(TOKEN_PATHS)} paths x 2 methods...\n")

    for path in TOKEN_PATHS:
        url = BASE + path
        for method in ("POST", "GET"):
            print("-" * 50)
            token = try_token(url, method, headers, data)
            if token:
                print(f"\nToken obtained (first 50 chars): {token[:50]}...")
                return token
    return None


def call_obligation(token):
    """Call the TC001 obligation endpoint with the test PIN."""
    url = BASE + OBLIGATION_PATH
    print(f"\nCalling TC001 obligation endpoint")
    print(f"  URL : {url}")
    print(f"  PIN : {TEST_PIN}")
    try:
        r = requests.post(
            url,
            json={"taxPayerPin": TEST_PIN},            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
            verify=False,
        )
        print(f"  Status: {r.status_code}")
        print(f"  Body  : {r.text[:500]}")
        if r.status_code == 200 and not is_html(r.text):
            try:
                body = r.json()
                # Success means Status OK, not just HTTP 200
                if body.get("Status") == "OK" or body.get("ResponseCode") == "00000":
                    return True
                else:
                    print(f"  API Status: {body.get('Status')} - {body.get('ResponseMsg', '')}")
                    return False
            except Exception:
                return False
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 60)
print("GavaConnect KRA TC001 Test")
print("=" * 60)

token = get_token()

if not token:
    print("\n" + "=" * 60)
    print("Could not obtain token from any candidate.")
    print("Next steps:")
    print("  1. Check the exact token URL on developer.go.ke app page")
    print("  2. Paste it into TOKEN_PATHS[0] in this script")
    print("  3. Confirm the sandbox host is sbx.kra.go.ke or similar")
    print("=" * 60)
    sys.exit(1)

passed = call_obligation(token)

# If default PIN failed, try other sandbox PINs
if not passed and TEST_PIN == "A011124346B":
    print("\nTrying other sandbox test PINs...")
    for pin in SANDBOX_TEST_PINS[1:]:
        TEST_PIN = pin
        passed = call_obligation(token)
        if passed:
            print(f"\nWorking sandbox PIN: {pin}")
            break

print("\n" + "=" * 60)
if passed:
    print("TC001 PASSED - take a screenshot of this output and the portal")
else:
    print("TC001 FAILED - check the obligation endpoint path and PIN")
    print(f"TODO: confirm OBLIGATION_PATH = {OBLIGATION_PATH!r}")
print("=" * 60)
