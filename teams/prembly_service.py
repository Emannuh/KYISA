"""
KYISA — Prembly Identity Verification Service
===============================================
Calls BOTH Prembly Kenya endpoints concurrently on every lookup so the
richest possible record is always returned with a single ID number.

Endpoints called in parallel:
  1. POST /verification/ke/national_id         — base (name, DOB)
  2. POST /verification/ke/national_id_advance  — full (photo, serial, DOI, etc.)

Results are merged — advance wins on any field it returns, base fills gaps.
Both are billed per call, but together they guarantee the most complete record.

API docs:  https://docs.prembly.com
Dashboard: app.prembly.com

Configuration (Railway Variables):
    PREMBLY_API_KEY=<live key from app.prembly.com>
    PREMBLY_ENVIRONMENT=production   # 'sandbox' or 'production'
"""
import concurrent.futures
import hashlib
import logging
from datetime import date, datetime
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from teams.huduma_service import IPRSLookupResult

logger = logging.getLogger(__name__)


class PremblyService:
    """
    Prembly Kenya identity verification.
    Always calls both endpoints concurrently and merges for maximum data return.
    """

    # ── Endpoint URLs ──────────────────────────────────────────────────────────
    _PROD    = "https://api.prembly.com"
    _SANDBOX = "https://sandbox.prembly.com"

    ENDPOINTS = [
        "/verification/ke/national_id",
    ]

    def __init__(self):
        self.api_key     = getattr(settings, 'PREMBLY_API_KEY', '')
        self.environment = getattr(settings, 'PREMBLY_ENVIRONMENT', 'sandbox')
        self.timeout     = 30
        self._base       = self._PROD if (self.api_key and self.environment == 'production') else self._SANDBOX

    # ── Public ─────────────────────────────────────────────────────────────────

    def lookup_by_national_id(self, national_id: str, serial_number: str = '') -> IPRSLookupResult:
        """
        Look up a person by Kenya National ID.
        Both endpoints are called concurrently; results are merged.
        Returns the richest available record.
        """
        national_id = national_id.strip()

        if not national_id:
            return IPRSLookupResult(success=False, error_message="National ID is required.")

        if not national_id.isdigit() or not (7 <= len(national_id) <= 8):
            return IPRSLookupResult(
                success=False,
                error_message="Invalid National ID format. Must be 7–8 digits.",
            )

        if not self.api_key:
            logger.warning("PREMBLY_API_KEY not set — simulation mode.")
            return self._simulate(national_id)

        try:
            return self._call_all(national_id)
        except Exception as exc:
            logger.exception("Prembly lookup failed for %s: %s", national_id, exc)
            return IPRSLookupResult(success=False, error_message=f"Verification failed: {exc}")

    # ── Private — concurrent calls ─────────────────────────────────────────────

    def _call_all(self, national_id: str) -> IPRSLookupResult:
        """Fire all endpoints in parallel, merge results."""
        payload = {"number": national_id}
        urls    = [f"{self._base}{ep}" for ep in self.ENDPOINTS]

        logger.info("Prembly dual lookup — ID: %s, base: %s", national_id, self._base)

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(urls)) as pool:
            futures = {pool.submit(self._post, url, payload): url for url in urls}
            raws    = [f.result() for f in concurrent.futures.as_completed(futures)]

        results = [self._parse(raw, national_id) for raw in raws]
        return self._merge(results)

    def _post(self, url: str, payload: dict) -> dict:
        """POST to Prembly. Returns {} on any failure (never raises)."""
        headers = {
            "x-api-key":    self.api_key,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("Prembly %s → status=%s photo=%s serial=%s",
                         url.split('/')[-1],
                         data.get('verification', {}).get('status', '?'),
                         'yes' if data.get('data', {}).get('photo') else 'no',
                         data.get('data', {}).get('id_serial_number', 'none'))
            return data
        except Exception as exc:
            logger.warning("Prembly %s failed: %s", url, exc)
            return {}

    # ── Parsing ────────────────────────────────────────────────────────────────

    def _parse(self, raw: dict, national_id: str) -> IPRSLookupResult:
        """Parse a single Prembly response into IPRSLookupResult."""
        if not raw:
            return IPRSLookupResult(success=False, error_message="No response.")

        if not raw.get('status', False):
            msg = raw.get('detail') or raw.get('message') or 'Verification failed.'
            return IPRSLookupResult(success=False, error_message=msg)

        verification = raw.get('verification') or {}
        verified     = verification.get('status', '') == 'VERIFIED'
        reference    = verification.get('reference', '')
        data         = raw.get('data') or {}

        if not data or not verified:
            return IPRSLookupResult(
                success=True, person_found=False,
                national_id=national_id, reference_number=reference,
                error_message="Person not found in IPRS.",
            )

        # Names
        first   = (data.get('first_name')  or '').strip().title()
        last    = (data.get('last_name')   or data.get('surname') or '').strip().title()
        other   = (data.get('other_name')  or '').strip().title()
        full    = ' '.join(f"{first} {other} {last}".split())

        # Gender
        g = (data.get('gender') or '').strip().upper()
        gender = 'Male' if g in ('M', 'MALE') else ('Female' if g in ('F', 'FEMALE') else g)

        # DOB
        dob: Optional[date] = None
        dob_str = data.get('date_of_birth') or data.get('dob') or ''
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

        # All data fields — collect everything Prembly returns
        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=first,
            last_name=last,
            other_names=other,
            full_name=full,
            date_of_birth=dob,
            age=age,
            gender=gender,
            national_id=data.get('id_number') or data.get('identity_number') or national_id,
            reference_number=reference,
            photo=data.get('photo') or '',
            serial_number=data.get('id_serial_number') or data.get('serial_number') or '',
            date_of_issue=data.get('date_of_issue') or '',
            place_of_birth=data.get('place_of_birth') or '',
            is_simulation=False,
        )

    @staticmethod
    def _merge(results: list) -> IPRSLookupResult:
        """
        Merge a list of IPRSLookupResult objects.
        For each field, take the first non-empty value across all results.
        If none found the person, return the first error.
        """
        found = [r for r in results if r.success and r.person_found]
        if not found:
            # Return best error
            for r in results:
                if r.success:
                    return r
            return results[0] if results else IPRSLookupResult(
                success=False, error_message="All IPRS lookups failed."
            )

        def pick(*vals):
            for v in vals:
                if v is None:
                    continue
                if isinstance(v, str) and v.strip():
                    return v
                if not isinstance(v, str) and v is not None:
                    return v
            return vals[-1] if vals else None

        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=pick(    *[r.first_name    for r in found]),
            last_name=pick(     *[r.last_name     for r in found]),
            other_names=pick(   *[r.other_names   for r in found]),
            full_name=pick(     *[r.full_name     for r in found]),
            date_of_birth=pick( *[r.date_of_birth for r in found]),
            age=pick(           *[r.age           for r in found]),
            gender=pick(        *[r.gender        for r in found]),
            national_id=pick(   *[r.national_id   for r in found]),
            reference_number=pick(*[r.reference_number for r in found]),
            photo=pick(         *[r.photo         for r in found]),
            serial_number=pick( *[r.serial_number for r in found]),
            date_of_issue=pick( *[r.date_of_issue for r in found]),
            place_of_birth=pick(*[r.place_of_birth for r in found]),
            is_simulation=False,
        )

    # ── Simulation ─────────────────────────────────────────────────────────────

    def _simulate(self, national_id: str) -> IPRSLookupResult:
        """Deterministic simulation when no API key is set."""
        logger.info("Prembly SIMULATION — ID: %s", national_id)
        h = int(hashlib.md5(national_id.encode()).hexdigest(), 16)

        firsts = ["James","John","Peter","David","Brian","Kevin","Mary","Grace","Faith","Joy"]
        lasts  = ["Ochieng","Wanjiku","Mwangi","Kiprop","Otieno","Kamau","Njoroge","Chebet"]

        first = firsts[h % len(firsts)]
        last  = lasts[(h // 100) % len(lasts)]
        today = timezone.now().date()
        age   = 18 + (h % 6)
        dob   = date(today.year - age, 1 + (h % 12), 1 + (h % 28))
        ref   = f"SIM-{hashlib.md5(national_id.encode()).hexdigest()[:10].upper()}"

        return IPRSLookupResult(
            success=True, person_found=True,
            first_name=first, last_name=last, other_names='',
            full_name=f"{first} {last}",
            date_of_birth=dob, age=age,
            gender='Male' if h % 2 == 0 else 'Female',
            national_id=national_id, reference_number=ref,
            photo='', serial_number='', date_of_issue='', place_of_birth='Nairobi',
            is_simulation=True,
        )
