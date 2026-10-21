"""
KYISA — Prembly Identity Verification Service
===============================================
Uses Prembly's Kenya endpoints to verify player identity against IPRS.

Two endpoints:
  1. National ID:  POST /verification/ke/national_id  — returns name/DOB only, no photo
  2. Serial Number: POST /verification/ke/serial       — returns full record incl. photo

We prefer the serial number endpoint when a serial is provided because it
returns the government photo. Fall back to national_id when serial is absent.

API docs: https://docs.prembly.com
Dashboard: app.prembly.com

Configuration (Railway environment variables):
    PREMBLY_API_KEY=live_sk_...
    PREMBLY_ENVIRONMENT=production   # 'sandbox' or 'production'
"""
import logging
import requests
from datetime import date, datetime
from typing import Optional

from django.conf import settings
from django.utils import timezone

from teams.huduma_service import IPRSLookupResult

logger = logging.getLogger(__name__)


class PremblyService:
    """
    Prembly Kenya identity verification service.
    Returns IPRSLookupResult — same interface used everywhere in the project.
    """

    # Basic national ID — returns name/DOB, photo often null
    NATIONAL_ID_URL_PROD    = "https://api.prembly.com/verification/ke/national_id"
    NATIONAL_ID_URL_SANDBOX = "https://sandbox.prembly.com/verification/ke/national_id"

    # Serial number — returns full record including photo
    SERIAL_URL_PROD    = "https://api.prembly.com/verification/ke/serial"
    SERIAL_URL_SANDBOX = "https://sandbox.prembly.com/verification/ke/serial"

    def __init__(self):
        self.api_key     = getattr(settings, 'PREMBLY_API_KEY', '')
        self.environment = getattr(settings, 'PREMBLY_ENVIRONMENT', 'sandbox')
        self.timeout     = 30
        self._is_live    = bool(self.api_key) and self.environment == 'production'

    # ── Public interface ───────────────────────────────────────────────────────

    def lookup_by_national_id(self, national_id: str, serial_number: str = '') -> IPRSLookupResult:
        """
        Look up a person by Kenya National ID number via Prembly IPRS.

        If serial_number is also provided, the serial endpoint is called first
        because it returns the full record including the government photo.
        Falls back to the basic national_id endpoint if serial is not given.

        Returns an IPRSLookupResult compatible with all existing views.
        """
        national_id   = national_id.strip()
        serial_number = serial_number.strip() if serial_number else ''

        if not national_id:
            return IPRSLookupResult(
                success=False,
                error_message="National ID is required.",
            )

        if not national_id.isdigit() or len(national_id) < 7 or len(national_id) > 8:
            return IPRSLookupResult(
                success=False,
                error_message="Invalid National ID format. Must be 7-8 digits.",
            )

        if not self.api_key:
            logger.warning("PREMBLY_API_KEY not set — using simulation mode.")
            return self._simulate(national_id)

        try:
            # Prefer serial endpoint — returns photo
            if serial_number:
                return self._call_serial(national_id, serial_number)
            else:
                return self._call_national_id(national_id)
        except Exception as exc:
            logger.exception("Prembly lookup error for ID %s: %s", national_id, exc)
            return IPRSLookupResult(
                success=False,
                error_message=f"Verification failed: {exc}",
            )

    def lookup_by_serial(self, national_id: str, serial_number: str) -> IPRSLookupResult:
        """
        Convenience method — explicitly call the serial endpoint.
        Use this when the county director provides the serial number from the back of the ID.
        """
        return self.lookup_by_national_id(national_id, serial_number=serial_number)

    # ── Private — API calls ────────────────────────────────────────────────────

    def _base_url(self, path_prod: str, path_sandbox: str) -> str:
        return path_prod if self._is_live else path_sandbox

    def _post(self, url: str, payload: dict) -> dict:
        """Make a POST request to Prembly and return parsed JSON."""
        headers = {
            "x-api-key":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            raise Exception("Verification timed out. Please try again.")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response else 0
            try:
                msg = exc.response.json().get("detail", exc.response.json().get("message", str(exc)))
            except Exception:
                msg = str(exc)
            raise Exception(f"Service error ({code}): {msg}")
        except requests.exceptions.RequestException as exc:
            raise Exception(f"Network error: {exc}")

    def _call_national_id(self, national_id: str) -> IPRSLookupResult:
        """Call the basic national ID endpoint — name/DOB only, photo rarely returned."""
        url = self._base_url(self.NATIONAL_ID_URL_PROD, self.NATIONAL_ID_URL_SANDBOX)
        logger.info("Prembly national_id lookup — ID: %s, env: %s", national_id, self.environment)
        raw = self._post(url, {"number": national_id})
        return self._parse_response(raw, national_id)

    def _call_serial(self, national_id: str, serial_number: str) -> IPRSLookupResult:
        """
        Call the serial number endpoint — returns full record including photo.
        The serial number is the alphanumeric code on the back of the Kenya National ID.
        """
        url = self._base_url(self.SERIAL_URL_PROD, self.SERIAL_URL_SANDBOX)
        logger.info(
            "Prembly serial lookup — ID: %s, serial: %s, env: %s",
            national_id, serial_number, self.environment
        )
        # Serial endpoint accepts the serial number as the lookup key
        raw = self._post(url, {"number": serial_number})
        return self._parse_response(raw, national_id)

    def _parse_response(self, raw: dict, national_id: str) -> IPRSLookupResult:
        """Parse any Prembly Kenya response into IPRSLookupResult."""

        if not raw.get('status', False):
            msg = raw.get('detail', raw.get('message', 'Verification failed.'))
            return IPRSLookupResult(success=False, error_message=msg)

        verification = raw.get('verification', {})
        verified     = verification.get('status', '') == 'VERIFIED'
        reference    = verification.get('reference', '')
        data         = raw.get('data', {})

        if not data or not verified:
            return IPRSLookupResult(
                success=True,
                person_found=False,
                national_id=national_id,
                reference_number=reference,
                error_message="Person not found in IPRS database.",
            )

        # Names — handle multiple field name variants across endpoints
        first_name  = (data.get('first_name', '') or '').strip().title()
        last_name   = (data.get('last_name', '') or data.get('surname', '') or '').strip().title()
        other_names = (data.get('other_name', '') or '').strip().title()
        full_name   = ' '.join(f"{first_name} {other_names} {last_name}".split())

        # Gender
        raw_gender = (data.get('gender', '') or '').strip().upper()
        gender = 'Male' if raw_gender in ('M', 'MALE') else ('Female' if raw_gender in ('F', 'FEMALE') else raw_gender)

        # DOB — try both field names the endpoints use
        dob: Optional[date] = None
        dob_str = data.get('date_of_birth') or data.get('dob', '')
        if dob_str:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%m/%d/%Y'):
                try:
                    dob = datetime.strptime(str(dob_str), fmt).date()
                    break
                except (ValueError, TypeError):
                    continue

        # Age
        age: Optional[int] = None
        if dob:
            today = timezone.now().date()
            age   = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        # Photo — the serial endpoint returns this; national_id often returns null
        photo = data.get('photo', '') or ''

        # Extra fields only the serial endpoint returns
        serial_number  = data.get('id_serial_number', '') or data.get('serial_number', '') or ''
        date_of_issue  = data.get('date_of_issue', '') or ''
        place_of_birth = data.get('place_of_birth', '') or ''

        logger.info(
            "Prembly result — ID: %s, name: %s, dob: %s, photo: %s, serial: %s, ref: %s",
            national_id, full_name, dob,
            'yes' if photo else 'no',
            serial_number or 'n/a',
            reference,
        )

        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=first_name,
            last_name=last_name,
            other_names=other_names,
            full_name=full_name,
            date_of_birth=dob,
            age=age,
            gender=gender,
            national_id=data.get('id_number', national_id),
            reference_number=reference,
            photo=photo,
            # Store extra fields in the result so callers can use them
            serial_number=serial_number,
            date_of_issue=date_of_issue,
            place_of_birth=place_of_birth,
            is_simulation=False,
        )

    # ── Simulation fallback ────────────────────────────────────────────────────

    def _simulate(self, national_id: str) -> IPRSLookupResult:
        """
        Deterministic simulation when no API key is configured.
        Returns realistic-looking data for development/demo.
        """
        import hashlib
        logger.info("Prembly SIMULATION mode — ID: %s", national_id)

        id_hash = int(hashlib.md5(national_id.encode()).hexdigest(), 16)

        first_names = [
            "James", "John", "Peter", "David", "Brian",
            "Kevin", "Dennis", "Daniel", "Michael", "Joseph",
            "Mary", "Grace", "Faith", "Joy", "Mercy",
            "Ann", "Sarah", "Lucy", "Jane", "Ruth",
        ]
        last_names = [
            "Ochieng", "Wanjiku", "Mwangi", "Kiprop", "Otieno",
            "Kamau", "Njoroge", "Chebet", "Mutua", "Wekesa",
        ]

        first = first_names[id_hash % len(first_names)]
        last  = last_names[(id_hash // 100) % len(last_names)]

        today      = timezone.now().date()
        age        = 18 + (id_hash % 6)
        birth_year = today.year - age
        dob        = date(birth_year, 1 + (id_hash % 12), 1 + (id_hash % 28))
        gender     = 'Male' if id_hash % 2 == 0 else 'Female'
        ref        = f"SIM-{hashlib.md5(national_id.encode()).hexdigest()[:10].upper()}"

        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=first,
            last_name=last,
            other_names='',
            full_name=f"{first} {last}",
            date_of_birth=dob,
            age=age,
            gender=gender,
            national_id=national_id,
            reference_number=ref,
            photo='',
            is_simulation=True,
        )
