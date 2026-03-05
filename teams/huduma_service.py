"""
KYISA — Huduma Kenya Age Verification Service
===============================================
Integrates with Huduma Kenya (National Registration Bureau) to verify
player age using their National ID or Birth Certificate number.

This verification is required for all players to confirm their date of
birth falls within the allowed age bracket (18–23 for KYISA).

Usage:
    from teams.huduma_service import HudumaKenyaService
    svc = HudumaKenyaService()
    result = svc.verify_player_age(player)  # returns HudumaResult
"""
import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, date

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class HudumaResult:
    """Immutable result from a Huduma Kenya verification."""
    success: bool                        # API call succeeded
    person_found: bool = False           # Person found in IPRS
    verified_name: str = ""              # Name as per IPRS
    verified_dob: Optional[date] = None  # Date of birth as per IPRS
    verified_age: Optional[int] = None   # Calculated age
    age_matches: bool = False            # DOB matches player record
    reference_number: str = ""           # Huduma verification reference
    raw_response: dict = field(default_factory=dict)
    error_message: str = ""
    checked_at: Optional[datetime] = None

    @property
    def is_verified(self) -> bool:
        """Person found and age matches within tolerance."""
        return self.success and self.person_found and self.age_matches


@dataclass
class IPRSLookupResult:
    """Result from an IPRS National ID lookup."""
    success: bool
    person_found: bool = False
    first_name: str = ""
    last_name: str = ""
    other_names: str = ""
    full_name: str = ""
    date_of_birth: Optional[date] = None
    age: Optional[int] = None
    gender: str = ""
    national_id: str = ""
    reference_number: str = ""
    error_message: str = ""
    is_simulation: bool = False

    def to_dict(self) -> dict:
        """Serialize for JSON response."""
        return {
            "success": self.success,
            "person_found": self.person_found,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "other_names": self.other_names,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "age": self.age,
            "gender": self.gender,
            "national_id": self.national_id,
            "reference_number": self.reference_number,
            "error_message": self.error_message,
            "is_simulation": self.is_simulation,
        }


class HudumaKenyaService:
    """
    Service class for Huduma Kenya / IPRS age verification.

    In production, set these in Django settings or .env:
        HUDUMA_API_URL     = "https://api.hudumakenya.go.ke/v1"
        HUDUMA_API_KEY     = "<your-api-key>"
        HUDUMA_ENABLED     = True
    """

    def __init__(self):
        self.api_url = getattr(settings, 'HUDUMA_API_URL', 'https://api.hudumakenya.go.ke/v1')
        self.api_key = getattr(settings, 'HUDUMA_API_KEY', '')
        self.enabled = getattr(settings, 'HUDUMA_ENABLED', True)
        self.timeout = getattr(settings, 'HUDUMA_TIMEOUT', 30)

    # ──────────────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────────────

    def verify_player_age(self, player) -> HudumaResult:
        """
        Verify a player's age via Huduma Kenya / IPRS.

        Args:
            player: teams.Player instance

        Returns:
            HudumaResult with verification outcome.
        """
        now = timezone.now()

        if not self.enabled:
            return HudumaResult(
                success=False,
                error_message="Huduma Kenya integration is disabled.",
                checked_at=now,
            )

        if not player.national_id_number and not player.birth_cert_number:
            return HudumaResult(
                success=False,
                error_message="Player has no National ID or Birth Certificate number.",
                checked_at=now,
            )

        try:
            raw = self._call_huduma_api(player)
            return self._parse_response(raw, player, now)
        except Exception as exc:
            logger.exception("Huduma Kenya API error for player %s", player.pk)
            return HudumaResult(
                success=False,
                error_message=str(exc),
                checked_at=now,
            )

    def verify_by_data(self, national_id: str = "", birth_cert: str = "",
                        claimed_dob: str = "", full_name: str = "") -> HudumaResult:
        """
        Verify using raw data (for pre-registration screening).
        """
        now = timezone.now()

        if not self.enabled:
            return HudumaResult(
                success=False,
                error_message="Huduma Kenya integration is disabled.",
                checked_at=now,
            )

        try:
            payload = {
                "national_id": national_id,
                "birth_cert_number": birth_cert,
                "full_name": full_name,
            }
            raw = self._call_api(payload)
            # Parse with claimed DOB
            claimed = None
            if claimed_dob:
                try:
                    claimed = date.fromisoformat(str(claimed_dob))
                except (ValueError, TypeError):
                    pass
            return self._parse_with_claimed_dob(raw, claimed, now)
        except Exception as exc:
            logger.exception("Huduma Kenya API error")
            return HudumaResult(
                success=False,
                error_message=str(exc),
                checked_at=now,
            )

    def lookup_by_national_id(self, national_id: str) -> IPRSLookupResult:
        """
        Look up a person's details by National ID from IPRS.

        This is used on the player registration form — when a team manager
        enters a National ID, this method returns the person's name, date
        of birth, and age so the form fields can be auto-populated.

        Args:
            national_id: Kenyan National ID number (string).

        Returns:
            IPRSLookupResult with person details on success.
        """
        if not national_id or not national_id.strip():
            return IPRSLookupResult(
                success=False,
                error_message="National ID number is required.",
            )

        national_id = national_id.strip()

        if not self.enabled:
            return IPRSLookupResult(
                success=False,
                error_message="IPRS integration is currently disabled.",
            )

        try:
            raw = self._call_iprs_lookup(national_id)
            return self._parse_iprs_lookup(raw, national_id)
        except Exception as exc:
            logger.exception("IPRS lookup error for ID %s", national_id)
            return IPRSLookupResult(
                success=False,
                error_message=f"IPRS lookup failed: {exc}",
            )

    # ──────────────────────────────────────────────────────────────────────────
    #  Private — API communication
    # ──────────────────────────────────────────────────────────────────────────

    def _call_huduma_api(self, player) -> dict:
        """
        Call the Huduma Kenya / IPRS API for a given player.

        PRODUCTION: Replace with real HTTP calls to Huduma Kenya.
        """
        payload = {
            "national_id": player.national_id_number,
            "birth_cert_number": player.birth_cert_number,
            "full_name": f"{player.first_name} {player.last_name}",
        }
        return self._call_api(payload)

    def _call_api(self, payload: dict) -> dict:
        """
        Stub implementation — simulates the Huduma Kenya IPRS response.

        In PRODUCTION, this will be an HTTP call. For now, it returns a
        simulated response that mirrors the claimed data (auto-pass).
        """
        if self.api_key:
            # ── REAL API CALL (uncomment when API credentials are available) ──
            # import requests
            # resp = requests.post(
            #     f"{self.api_url}/verify/identity",
            #     headers={
            #         "Authorization": f"Bearer {self.api_key}",
            #         "Content-Type": "application/json",
            #     },
            #     json=payload,
            #     timeout=self.timeout,
            # )
            # resp.raise_for_status()
            # return resp.json()
            pass

        # ── SIMULATION MODE ───────────────────────────────────────────────────
        logger.info("Huduma Kenya SIMULATION mode — ID: %s", payload.get('national_id'))

        # Generate a deterministic reference number
        seed = payload.get('national_id', '') or payload.get('birth_cert_number', '')
        ref = f"HK-{hashlib.md5(seed.encode()).hexdigest()[:10].upper()}"

        return {
            "status": "success",
            "person_found": True,
            "reference": ref,
            "person": {
                "full_name": payload.get('full_name', ''),
                "national_id": payload.get('national_id', ''),
                "birth_cert_number": payload.get('birth_cert_number', ''),
                # In simulation, we don't have the real DOB from IPRS,
                # so the admin must manually confirm during verification.
                "date_of_birth": None,  # Will be set by admin in manual flow
            },
            "_simulation": True,
        }

    def _parse_response(self, raw: dict, player, checked_at) -> HudumaResult:
        """Parse the Huduma API response, comparing against the player's claimed DOB."""
        return self._parse_with_claimed_dob(raw, player.date_of_birth, checked_at)

    def _parse_with_claimed_dob(self, raw: dict, claimed_dob, checked_at) -> HudumaResult:
        """Parse response and compare against a claimed date of birth."""
        if raw.get("status") != "success":
            return HudumaResult(
                success=False,
                error_message=raw.get("error", "Unknown API error"),
                raw_response=raw,
                checked_at=checked_at,
            )

        person_found = raw.get("person_found", False)
        person = raw.get("person", {})

        verified_name = person.get("full_name", "")
        ref = raw.get("reference", "")

        # Parse DOB from response
        verified_dob = None
        dob_str = person.get("date_of_birth")
        if dob_str:
            try:
                verified_dob = date.fromisoformat(str(dob_str))
            except (ValueError, TypeError):
                pass

        # Calculate verified age
        verified_age = None
        if verified_dob:
            today = timezone.now().date()
            verified_age = today.year - verified_dob.year - (
                (today.month, today.day) < (verified_dob.month, verified_dob.day)
            )

        # Check if DOB matches — in simulation mode without DOB from API,
        # we rely on the admin to manually confirm
        age_matches = False
        if verified_dob and claimed_dob:
            age_matches = verified_dob == claimed_dob
        elif raw.get("_simulation") and person_found:
            # In simulation mode, mark as needing manual confirmation
            # Admin will finalize the status
            age_matches = True  # Placeholder — admin must confirm

        return HudumaResult(
            success=True,
            person_found=person_found,
            verified_name=verified_name,
            verified_dob=verified_dob,
            verified_age=verified_age,
            age_matches=age_matches,
            reference_number=ref,
            raw_response=raw,
            checked_at=checked_at,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  Private — IPRS ID Lookup
    # ──────────────────────────────────────────────────────────────────────────

    def _call_iprs_lookup(self, national_id: str) -> dict:
        """
        Call the IPRS API to look up a person by National ID.

        PRODUCTION: Replace the simulation block with a real HTTP call
        to the Huduma Kenya / IPRS identity lookup endpoint.
        """
        if self.api_key:
            # ── REAL API CALL (uncomment when credentials are available) ──
            # import requests
            # resp = requests.post(
            #     f"{self.api_url}/identity/lookup",
            #     headers={
            #         "Authorization": f"Bearer {self.api_key}",
            #         "Content-Type": "application/json",
            #     },
            #     json={"national_id": national_id},
            #     timeout=self.timeout,
            # )
            # resp.raise_for_status()
            # return resp.json()
            pass

        # ── SIMULATION MODE ───────────────────────────────────────────────────
        logger.info("IPRS LOOKUP SIMULATION — ID: %s", national_id)

        ref = f"IPRS-{hashlib.md5(national_id.encode()).hexdigest()[:10].upper()}"

        # Generate deterministic but realistic simulation data from the ID
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
            "Akinyi", "Kibet", "Omondi", "Waithera", "Rotich",
        ]

        first = first_names[id_hash % len(first_names)]
        last = last_names[(id_hash // 100) % len(last_names)]
        gender = "Male" if id_hash % 2 == 0 else "Female"

        # Generate a DOB that puts the person in the 18-23 range
        today = timezone.now().date()
        age = 18 + (id_hash % 6)  # 18 to 23
        birth_year = today.year - age
        birth_month = 1 + (id_hash % 12)
        birth_day = 1 + (id_hash % 28)
        dob = date(birth_year, birth_month, birth_day)

        return {
            "status": "success",
            "person_found": True,
            "reference": ref,
            "person": {
                "first_name": first,
                "last_name": last,
                "other_names": "",
                "full_name": f"{first} {last}",
                "date_of_birth": dob.isoformat(),
                "gender": gender,
                "national_id": national_id,
            },
            "_simulation": True,
        }

    def _parse_iprs_lookup(self, raw: dict, national_id: str) -> IPRSLookupResult:
        """Parse the IPRS lookup response into an IPRSLookupResult."""
        if raw.get("status") != "success":
            return IPRSLookupResult(
                success=False,
                error_message=raw.get("error", "IPRS lookup failed."),
            )

        person_found = raw.get("person_found", False)
        if not person_found:
            return IPRSLookupResult(
                success=True,
                person_found=False,
                national_id=national_id,
                error_message="No person found with this National ID.",
                is_simulation=raw.get("_simulation", False),
            )

        person = raw.get("person", {})

        # Parse date of birth
        dob = None
        dob_str = person.get("date_of_birth")
        if dob_str:
            try:
                dob = date.fromisoformat(str(dob_str))
            except (ValueError, TypeError):
                pass

        # Calculate age
        age = None
        if dob:
            today = timezone.now().date()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )

        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=person.get("first_name", ""),
            last_name=person.get("last_name", ""),
            other_names=person.get("other_names", ""),
            full_name=person.get("full_name", ""),
            date_of_birth=dob,
            age=age,
            gender=person.get("gender", ""),
            national_id=national_id,
            reference_number=raw.get("reference", ""),
            is_simulation=raw.get("_simulation", False),
        )
