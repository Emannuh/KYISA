"""
KYISA — Prembly Identity Verification Service
===============================================
Replaces Smile Identity for Kenya IPRS (National ID) lookups.
Uses Prembly's Kenya National ID endpoint to verify player identity
against the government IPRS database.

API endpoint: POST https://api.prembly.com/verification/ke/national_id
Sandbox:      POST https://sandbox.prembly.com/verification/ke/national_id
Test ID:      10101010

Pricing: pay-per-lookup.
Dashboard: app.prembly.com

Configuration (Railway environment variables):
    PREMBLY_API_KEY=live_sk_...         # your Prembly API key
    PREMBLY_ENVIRONMENT=sandbox         # 'sandbox' or 'production'

Usage:
    from teams.prembly_service import PremblyService
    svc = PremblyService()
    result = svc.lookup_by_national_id("12345678")  # returns IPRSLookupResult
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
    Prembly Kenya National ID verification service.
    Drop-in replacement for HudumaKenyaService IPRS calls.
    Returns IPRSLookupResult — same interface used everywhere in the project.
    """

    PRODUCTION_URL = "https://api.prembly.com/verification/ke/national_id"
    SANDBOX_URL    = "https://sandbox.prembly.com/verification/ke/national_id"

    def __init__(self):
        self.api_key     = getattr(settings, 'PREMBLY_API_KEY', '')
        self.environment = getattr(settings, 'PREMBLY_ENVIRONMENT', 'sandbox')
        self.timeout     = 30
        self._is_live    = bool(self.api_key) and self.environment == 'production'
        self._is_sandbox = bool(self.api_key) and self.environment == 'sandbox'
        self.base_url    = self.PRODUCTION_URL if self._is_live else self.SANDBOX_URL

    # ── Public interface ───────────────────────────────────────────────────────

    def lookup_by_national_id(self, national_id: str) -> IPRSLookupResult:
        """
        Look up a person by Kenya National ID number via Prembly IPRS.
        Returns an IPRSLookupResult — compatible with all existing views.
        """
        national_id = national_id.strip()

        if not national_id:
            return IPRSLookupResult(
                success=False,
                error_message="National ID is required.",
            )

        # Validate format — Kenyan IDs are 7-8 digits
        if not national_id.isdigit() or len(national_id) < 7 or len(national_id) > 8:
            return IPRSLookupResult(
                success=False,
                error_message="Invalid National ID format. Must be 7-8 digits.",
            )

        # No API key — fall back to simulation
        if not self.api_key:
            logger.warning("PREMBLY_API_KEY not set — using simulation mode.")
            return self._simulate(national_id)

        try:
            return self._call_prembly(national_id)
        except Exception as exc:
            logger.exception("Prembly lookup error for ID %s: %s", national_id, exc)
            return IPRSLookupResult(
                success=False,
                error_message=f"Verification failed: {exc}",
            )

    # ── Private — API call ─────────────────────────────────────────────────────

    def _call_prembly(self, national_id: str) -> IPRSLookupResult:
        """POST to Prembly Kenya National ID endpoint."""
        headers = {
            "x-api-key":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        payload = {"number": national_id}

        logger.info(
            "Prembly IPRS lookup — ID: %s, env: %s",
            national_id, self.environment
        )

        try:
            resp = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.exceptions.Timeout:
            logger.error("Prembly timeout for ID %s", national_id)
            return IPRSLookupResult(
                success=False,
                error_message="Verification timed out. Please try again.",
            )
        except requests.exceptions.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else 0
            try:
                body = exc.response.json()
                msg  = body.get("detail", body.get("message", str(exc)))
            except Exception:
                msg = str(exc)
            logger.error(
                "Prembly HTTP %s for ID %s: %s", status_code, national_id, msg
            )
            return IPRSLookupResult(
                success=False,
                error_message=f"Verification service error ({status_code}): {msg}",
            )
        except requests.exceptions.RequestException as exc:
            logger.exception("Prembly network error for ID %s", national_id)
            return IPRSLookupResult(
                success=False,
                error_message=f"Network error: {exc}",
            )

        return self._parse_response(raw, national_id)

    def _parse_response(self, raw: dict, national_id: str) -> IPRSLookupResult:
        """
        Parse Prembly's Kenya National ID response into IPRSLookupResult.

        Prembly response shape:
        {
            "status": true,
            "detail": "Verification successful",
            "response_code": "00",
            "data": {
                "first_name": "JOHN",
                "last_name": "DOE",
                "other_name": "PETER",
                "date_of_birth": "1998-05-14",
                "gender": "M",
                "id_number": "12345678",
                "citizenship": "KENYAN",
                "photo": "base64...",
                ...
            },
            "verification": {
                "status": "VERIFIED",
                "reference": "uuid-..."
            }
        }
        """
        # Check top-level status
        if not raw.get('status', False):
            msg = raw.get('detail', raw.get('message', 'Verification failed.'))
            return IPRSLookupResult(
                success=False,
                error_message=msg,
            )

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

        # Parse names
        first_name  = (data.get('first_name', '') or '').strip().title()
        last_name   = (data.get('last_name',  '') or data.get('surname', '')).strip().title()
        other_names = (data.get('other_name', '') or '').strip().title()
        full_name   = f"{first_name} {other_names} {last_name}".strip()
        full_name   = ' '.join(full_name.split())  # collapse extra spaces

        # Parse gender
        raw_gender = (data.get('gender', '') or '').strip().upper()
        if raw_gender in ('M', 'MALE'):
            gender = 'Male'
        elif raw_gender in ('F', 'FEMALE'):
            gender = 'Female'
        else:
            gender = raw_gender

        # Parse date of birth
        dob: Optional[date] = None
        dob_str = data.get('date_of_birth') or data.get('dob', '')
        if dob_str:
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
                try:
                    dob = datetime.strptime(str(dob_str), fmt).date()
                    break
                except (ValueError, TypeError):
                    continue

        # Calculate age
        age: Optional[int] = None
        if dob:
            today = timezone.now().date()
            age   = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )

        # Photo (base64)
        photo = data.get('photo', '') or ''

        logger.info(
            "Prembly IPRS result — ID: %s, name: %s, dob: %s, ref: %s",
            national_id, full_name, dob, reference
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
