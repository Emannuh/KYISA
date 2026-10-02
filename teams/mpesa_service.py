"""
KYISA — M-Pesa Daraja API Integration (STK Push / Lipa Na M-Pesa Online)
Sends a payment prompt to the user's phone. Funds go to the configured
business shortcode which can be linked to a bank account via Safaricom.
"""
import base64
import hashlib
import hmac
import logging
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Daraja API endpoints
SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"

# Safaricom published callback IP ranges (production).
# Requests from the callback URL must originate from these CIDRs.
# Source: https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate
SAFARICOM_CALLBACK_IPS = {
    "196.201.214.200",
    "196.201.214.206",
    "196.201.213.114",
    "196.201.214.207",
    "196.201.214.208",
    "196.201.213.44",
    "196.201.212.127",
    "196.201.212.138",
    "196.201.212.129",
    "196.201.212.136",
    "196.201.212.74",
    "196.201.212.69",
}

# In sandbox mode we accept any IP so developers can test locally.
SANDBOX_BYPASS_IP_CHECK = True


def _get_base_url():
    if getattr(settings, "MPESA_ENVIRONMENT", "sandbox") == "production":
        return PRODUCTION_BASE
    return SANDBOX_BASE


def _get_access_token():
    """Fetch OAuth access token from Daraja API."""
    url = f"{_get_base_url()}/oauth/v1/generate?grant_type=client_credentials"
    key = getattr(settings, "MPESA_CONSUMER_KEY", "")
    secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
    if not key or not secret:
        raise ValueError("M-Pesa consumer key/secret not configured in settings.")
    resp = requests.get(url, auth=(key, secret), timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _generate_password(shortcode, passkey, timestamp):
    """Base64-encode(shortcode + passkey + timestamp)."""
    data = f"{shortcode}{passkey}{timestamp}"
    return base64.b64encode(data.encode("utf-8")).decode("utf-8")


def initiate_stk_push(phone_number, amount, account_reference=None, description=None):
    """
    Send an STK push (Lipa Na M-Pesa Online) to the given phone number.

    Args:
        phone_number: Kenyan phone in +254XXXXXXXXX or 254XXXXXXXXX format.
        amount: Amount in KSh (integer).
        account_reference: Reference shown on M-Pesa receipt.
        description: Transaction description.

    Returns:
        dict with keys: success (bool), data (API response dict or error string).
    """
    shortcode = getattr(settings, "MPESA_SHORTCODE", "")
    passkey = getattr(settings, "MPESA_PASSKEY", "")
    callback_url = getattr(settings, "MPESA_CALLBACK_URL", "")

    if not all([shortcode, passkey, callback_url]):
        return {
            "success": False,
            "data": "M-Pesa is not fully configured. Please contact KYISA admin.",
        }

    # Normalise phone: strip +, ensure starts with 254
    phone = phone_number.replace("+", "").replace(" ", "")
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif not phone.startswith("254"):
        phone = "254" + phone

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = _generate_password(shortcode, passkey, timestamp)

    if not account_reference:
        account_reference = getattr(settings, "MPESA_ACCOUNT_REF", "KYISA2026")
    if not description:
        description = "KYISA County Registration Fee"

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": shortcode,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }

    try:
        token = _get_access_token()
        url = f"{_get_base_url()}/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()

        if result.get("ResponseCode") == "0":
            logger.info("STK push sent to %s — CheckoutRequestID: %s",
                        phone, result.get("CheckoutRequestID"))
            return {"success": True, "data": result}
        else:
            logger.warning("STK push failed: %s", result)
            return {"success": False, "data": result.get("ResponseDescription", "STK push failed.")}

    except requests.RequestException as e:
        logger.error("M-Pesa API error: %s", e)
        return {"success": False, "data": f"Network error contacting M-Pesa: {e}"}
    except Exception as e:
        logger.error("M-Pesa unexpected error: %s", e)
        return {"success": False, "data": str(e)}


def query_stk_push_status(checkout_request_id):
    """
    Query the status of a previously initiated STK push.

    Returns:
        dict with keys: success (bool), data (API response dict or error string).
    """
    shortcode = getattr(settings, "MPESA_SHORTCODE", "")
    passkey = getattr(settings, "MPESA_PASSKEY", "")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = _generate_password(shortcode, passkey, timestamp)

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    try:
        token = _get_access_token()
        url = f"{_get_base_url()}/mpesa/stkpushquery/v1/query"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return {"success": True, "data": resp.json()}
    except Exception as e:
        logger.error("STK query error: %s", e)
        return {"success": False, "data": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
#  CALLBACK VALIDATION
# ──────────────────────────────────────────────────────────────────────────────

def _get_client_ip(request) -> str:
    """Extract the real client IP, honouring X-Forwarded-For from trusted proxies."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def validate_callback_ip(request) -> bool:
    """
    Return True if the request originates from a known Safaricom IP.
    Always returns True in sandbox mode so local testing works.
    """
    environment = getattr(settings, "MPESA_ENVIRONMENT", "sandbox")
    if environment != "production":
        return True  # sandbox — skip IP check

    client_ip = _get_client_ip(request)
    if client_ip not in SAFARICOM_CALLBACK_IPS:
        logger.warning(
            "M-Pesa callback rejected: unexpected source IP %s", client_ip
        )
        return False
    return True


def validate_checkout_id(checkout_request_id: str) -> bool:
    """
    Confirm the CheckoutRequestID in the callback matches one we actually
    initiated.  IDs are stored on CountyRegistration.mpesa_checkout_id.

    Returns True if found, False otherwise.
    """
    from teams.models import CountyRegistration

    exists = CountyRegistration.objects.filter(
        mpesa_checkout_id=checkout_request_id
    ).exists()
    if not exists:
        logger.warning(
            "M-Pesa callback with unknown CheckoutRequestID: %s",
            checkout_request_id,
        )
    return exists


def process_stk_callback(body: dict) -> dict:
    """
    Parse and apply a Safaricom STK push callback payload.

    Expected body structure (Daraja V1):
    {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "...",
                "CheckoutRequestID": "...",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount",          "Value": 250000},
                        {"Name": "MpesaReceiptNumber","Value": "ABC123XYZ"},
                        {"Name": "TransactionDate",  "Value": 20260101120000},
                        {"Name": "PhoneNumber",      "Value": 254712345678}
                    ]
                }
            }
        }
    }

    Returns {"success": bool, "message": str}.
    """
    from django.utils import timezone
    from teams.models import CountyRegistration, CountyRegStatus

    try:
        callback = body["Body"]["stkCallback"]
    except (KeyError, TypeError):
        logger.error("M-Pesa callback: malformed body — %s", body)
        return {"success": False, "message": "Malformed callback body."}

    checkout_id = callback.get("CheckoutRequestID", "")
    result_code = callback.get("ResultCode")
    result_desc = callback.get("ResultDesc", "")

    # Locate the registration that initiated this push
    try:
        reg = CountyRegistration.objects.get(mpesa_checkout_id=checkout_id)
    except CountyRegistration.DoesNotExist:
        logger.warning(
            "M-Pesa callback: no CountyRegistration for CheckoutRequestID %s",
            checkout_id,
        )
        return {"success": False, "message": "Unknown CheckoutRequestID."}

    if result_code != 0:
        # Payment failed or was cancelled by the user
        logger.info(
            "M-Pesa STK callback: payment not completed for %s — code %s (%s)",
            reg.county, result_code, result_desc,
        )
        return {
            "success": False,
            "message": f"Payment not completed: {result_desc}",
        }

    # Extract metadata items
    items = {}
    for item in callback.get("CallbackMetadata", {}).get("Item", []):
        items[item.get("Name")] = item.get("Value")

    mpesa_ref  = str(items.get("MpesaReceiptNumber", ""))
    amount     = items.get("Amount")
    phone      = str(items.get("PhoneNumber", ""))

    if not mpesa_ref:
        logger.error("M-Pesa callback: no MpesaReceiptNumber in metadata — %s", items)
        return {"success": False, "message": "Missing MpesaReceiptNumber in callback."}

    # Update the registration record
    reg.mpesa_reference = mpesa_ref
    reg.mpesa_phone     = phone
    if amount:
        reg.payment_amount = amount
    reg.payment_method       = "mpesa"
    reg.payment_submitted_at = timezone.now()
    reg.status               = CountyRegStatus.PAYMENT_SUBMITTED
    reg.save(update_fields=[
        "mpesa_reference", "mpesa_phone", "payment_amount",
        "payment_method", "payment_submitted_at", "status",
    ])

    logger.info(
        "M-Pesa payment recorded for %s — ref %s, amount %s",
        reg.county, mpesa_ref, amount,
    )
    return {
        "success": True,
        "message": f"Payment {mpesa_ref} recorded for {reg.county}.",
    }
