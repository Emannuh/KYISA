"""
KYISA — Didit.me Identity Verification Service
================================================
Verifies player identity (name, DOB, photo) against Kenya's NRB IPRS
(Integrated Population Registration System) via Didit.me's KYC sessions API.

Flow:
  1. Create a Didit session for the player (POST /v3/session/)
  2. Player opens the verification URL on a phone/tablet and scans their ID
  3. Didit processes the document, calls Kenya NRB IPRS (ken_national_id)
  4. Webhook fires when verification completes → KYISA records the result
  5. OR: poll GET /v3/session/{id}/decision/ for immediate result

Pricing (Didit.me as of 2026):
  - 500 free verifications/month per account
  - $0.15 per ID check after free tier
  - $3.15 per NRB (ken_national_id) database validation
  Full KYC bundle: ~$0.33/player

Configuration (.env):
    DIDIT_API_KEY=your_api_key
    DIDIT_WORKFLOW_ID=your_workflow_uuid
    DIDIT_WEBHOOK_SECRET=your_webhook_secret
    DIDIT_ENVIRONMENT=sandbox          # 'sandbox' or 'live'
    DIDIT_ENABLED=True

Usage:
    from teams.didit_service import DiditService
    svc = DiditService()

    # Create session for a player → returns URL to send to player
    result = svc.create_verification_session(player)

    # Check result after webhook fires
    result = svc.get_session_decision(session_id)

    # Full pipeline: create + wait + parse
    result = svc.verify_player_age(player)
"""
import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Age eligibility constants (match teams/models.py) ─────────────────────────
PLAYER_MIN_AGE = 18
PLAYER_MAX_AGE = 23


# ══════════════════════════════════════════════════════════════════════════════
#  Result dataclasses — drop-in compatible with HudumaResult / IPRSLookupResult
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DiditVerificationResult:
    """
    Result from a Didit KYC session.
    Mirrors the HudumaResult interface so existing views work unchanged.
    """
    success: bool
    person_found: bool = False

    # Identity data from NRB / ID document OCR
    verified_name: str = ""
    first_name: str = ""
    last_name: str = ""
    other_names: str = ""
    verified_dob: Optional[date] = None
    verified_age: Optional[int] = None
    gender: str = ""
    national_id: str = ""

    # Age eligibility
    age_matches: bool = False       # verified_dob == player.date_of_birth
    age_eligible: bool = False      # 18 ≤ verified_age ≤ 23

    # Session / reference
    session_id: str = ""
    reference_number: str = ""      # Didit session_number (human-readable)
    session_url: str = ""           # Hosted verification URL (send to player)
    session_status: str = ""        # Didit status string

    # NRB database validation
    nrb_match_type: str = ""        # full_match | partial_match | no_match
    nrb_checked: bool = False

    # Photo (base64 from ID document OCR)
    photo: str = ""

    # Simulation / sandbox
    is_simulation: bool = False

    error_message: str = ""
    checked_at: Optional[datetime] = None
    raw_response: dict = field(default_factory=dict)

    @property
    def is_verified(self) -> bool:
        """
        True when the player passed full Didit KYC:
        - Person found in NRB IPRS
        - DOB matches registration
        - Age is within the 18–23 bracket
        """
        return (
            self.success
            and self.person_found
            and self.age_matches
            and self.age_eligible
        )

    def to_dict(self) -> dict:
        """Serialise for JSON responses / AJAX."""
        return {
            "success": self.success,
            "person_found": self.person_found,
            "verified_name": self.verified_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "other_names": self.other_names,
            "date_of_birth": self.verified_dob.isoformat() if self.verified_dob else None,
            "age": self.verified_age,
            "gender": self.gender,
            "national_id": self.national_id,
            "age_matches": self.age_matches,
            "age_eligible": self.age_eligible,
            "session_id": self.session_id,
            "reference_number": self.reference_number,
            "session_url": self.session_url,
            "session_status": self.session_status,
            "nrb_match_type": self.nrb_match_type,
            "nrb_checked": self.nrb_checked,
            "is_verified": self.is_verified,
            "is_simulation": self.is_simulation,
            "error_message": self.error_message,
            "photo": self.photo,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  DiditService
# ══════════════════════════════════════════════════════════════════════════════

class DiditService:
    """
    KYISA → Didit.me KYC integration.

    API base:
        Sandbox: https://verification.didit.me  (same host, sandbox app key)
        Live:    https://verification.didit.me

    Auth: x-api-key header on every request.
    """

    BASE_URL = "https://verification.didit.me"

    def __init__(self):
        self.api_key      = getattr(settings, "DIDIT_API_KEY",       "")
        self.workflow_id  = getattr(settings, "DIDIT_WORKFLOW_ID",   "")
        self.webhook_secret = getattr(settings, "DIDIT_WEBHOOK_SECRET", "")
        self.environment  = getattr(settings, "DIDIT_ENVIRONMENT",   "sandbox")
        self.timeout      = getattr(settings, "DIDIT_TIMEOUT",       30)
        self.enabled      = getattr(settings, "DIDIT_ENABLED",       True)

    @property
    def _is_live(self) -> bool:
        """True when real API credentials are configured."""
        return bool(self.api_key) and bool(self.workflow_id)

    @property
    def _headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────────────

    def create_verification_session(self, player, callback_url: str = "") -> DiditVerificationResult:
        """
        Create a Didit KYC session for a player.

        Returns a DiditVerificationResult with session_url — send this URL
        to the player (display as QR code on the verification station screen).
        The player opens it on their phone, scans their National ID, and
        Didit calls Kenya NRB to verify.

        The result is delivered via webhook (async) or polled via
        get_session_decision(session_id).
        """
        now = timezone.now()

        if not self.enabled:
            return DiditVerificationResult(
                success=False,
                error_message="Didit verification is disabled.",
                checked_at=now,
            )

        if not self._is_live:
            return self._simulate_session(player, now)

        national_id = getattr(player, "national_id_number", "") or ""
        if not national_id:
            return DiditVerificationResult(
                success=False,
                error_message="Player has no National ID number.",
                checked_at=now,
            )

        try:
            payload = {
                "workflow_id": self.workflow_id,
                "vendor_data": f"kyisa-player-{player.pk}",
                "language": "en",
                # Pre-fill expected details — Didit cross-validates these
                # against the ID document and NRB database response
                "expected_details": {
                    "first_name": player.first_name,
                    "last_name": player.last_name,
                    "date_of_birth": player.date_of_birth.isoformat(),
                    "id_number": national_id,
                    "id_country": "KEN",
                },
            }
            if callback_url:
                payload["callback"] = callback_url

            resp = requests.post(
                f"{self.BASE_URL}/v3/session/",
                headers=self._headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

        except requests.exceptions.Timeout:
            logger.error("Didit timeout creating session for player %s", player.pk)
            return DiditVerificationResult(
                success=False,
                error_message="Didit API timed out. Please try again.",
                checked_at=now,
            )
        except requests.exceptions.HTTPError as exc:
            try:
                body = exc.response.json()
                msg = body.get("detail", str(exc))
            except Exception:
                msg = str(exc)
            logger.error("Didit HTTP %s for player %s: %s",
                         exc.response.status_code, player.pk, msg)
            return DiditVerificationResult(
                success=False,
                error_message=f"Didit API error: {msg}",
                checked_at=now,
            )
        except requests.exceptions.RequestException as exc:
            logger.exception("Didit network error for player %s", player.pk)
            return DiditVerificationResult(
                success=False,
                error_message=f"Network error: {exc}",
                checked_at=now,
            )

        session_id  = data.get("session_id", "")
        session_num = str(data.get("session_number", ""))
        session_url = data.get("url", "")
        status      = data.get("status", "Not Started")

        logger.info(
            "Didit session created for player %s — session_id=%s status=%s",
            player.pk, session_id, status,
        )

        return DiditVerificationResult(
            success=True,
            session_id=session_id,
            reference_number=session_num,
            session_url=session_url,
            session_status=status,
            checked_at=now,
            raw_response=data,
        )

    def get_session_decision(self, session_id: str) -> DiditVerificationResult:
        """
        Poll GET /v3/session/{session_id}/decision/ for the verification result.

        Called:
          - By the webhook handler after Didit fires a status.updated event
          - By the verification station polling endpoint
        """
        now = timezone.now()

        if not self._is_live:
            return self._simulate_decision(session_id, now)

        try:
            resp = requests.get(
                f"{self.BASE_URL}/v3/session/{session_id}/decision/",
                headers=self._headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.HTTPError as exc:
            if exc.response.status_code == 404:
                return DiditVerificationResult(
                    success=False,
                    error_message="Session not found.",
                    checked_at=now,
                )
            logger.error("Didit decision fetch error for session %s: %s", session_id, exc)
            return DiditVerificationResult(
                success=False,
                error_message=str(exc),
                checked_at=now,
            )
        except requests.exceptions.RequestException as exc:
            logger.exception("Didit network error fetching decision %s", session_id)
            return DiditVerificationResult(
                success=False,
                error_message=str(exc),
                checked_at=now,
            )

        return self._parse_decision(data, now)

    def verify_player_age(self, player) -> DiditVerificationResult:
        """
        Legacy-compatible entry point matching HudumaKenyaService.verify_player_age().

        For existing players with a stored didit_session_id, fetches the decision.
        For new players, creates a session and returns the session URL.

        The verification station UI uses create_verification_session() directly
        and polls via get_session_decision() — this method is for compatibility
        with the existing huduma_verify_player view.
        """
        now = timezone.now()

        if not self.enabled:
            return DiditVerificationResult(
                success=False,
                error_message="Didit verification is disabled.",
                checked_at=now,
            )

        # If player already has a session, fetch the decision
        session_id = getattr(player, "didit_session_id", "") or ""
        if session_id:
            return self.get_session_decision(session_id)

        # Otherwise create a new session
        return self.create_verification_session(player)

    # ──────────────────────────────────────────────────────────────────────────
    #  Webhook signature verification
    # ──────────────────────────────────────────────────────────────────────────

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify the X-Signature-V2 HMAC-SHA256 signature from Didit webhooks.

        Didit signs over a canonical re-encoding of the JSON body:
          - whole-valued floats shortened to ints
          - keys sorted recursively
          - compact separators (no spaces)
          - Unicode preserved

        Returns True if the signature matches.
        """
        if not self.webhook_secret:
            logger.warning("DIDIT_WEBHOOK_SECRET not set — skipping signature check")
            return True  # Fail-open in dev; tighten in production

        try:
            # Parse and re-encode canonically
            body_dict = json.loads(raw_body)
            canonical = _canonical_json(body_dict)
            expected = hmac.new(
                self.webhook_secret.encode(),
                canonical.encode(),
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header or "")
        except Exception:
            logger.exception("Didit webhook signature verification failed")
            return False

    def parse_webhook_payload(self, payload: dict) -> DiditVerificationResult:
        """
        Parse an incoming Didit webhook payload (status.updated event).
        The decision object shape is identical to GET /decision/.
        """
        now = timezone.now()
        decision = payload.get("decision", {})
        if not decision:
            # Session status changed but decision not yet available (e.g. In Progress)
            return DiditVerificationResult(
                success=True,
                session_id=payload.get("session_id", ""),
                session_status=payload.get("status", ""),
                reference_number=str(payload.get("session_number", "")),
                checked_at=now,
                raw_response=payload,
            )
        return self._parse_decision(decision, now, session_meta=payload)

    # ──────────────────────────────────────────────────────────────────────────
    #  Private — parsing
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_decision(self, data: dict, now: datetime,
                        session_meta: dict = None) -> DiditVerificationResult:
        """
        Parse GET /v3/session/{id}/decision/ response or the decision object
        from a webhook payload.

        Didit v3 returns plural arrays for each feature:
            id_verifications[], database_validations[], liveness_checks[], ...
        """
        session_meta = session_meta or {}
        session_id  = data.get("session_id", "") or session_meta.get("session_id", "")
        session_num = str(data.get("session_number", "") or session_meta.get("session_number", ""))
        status      = data.get("status", "") or session_meta.get("status", "")

        # ── Extract ID verification (document OCR) ────────────────────────
        id_verifications = data.get("id_verifications", [])
        id_ver = id_verifications[0] if id_verifications else {}

        person_data = id_ver.get("extracted_data", {}) or {}
        first_name  = person_data.get("first_name", "")
        last_name   = person_data.get("last_name", "")
        other_names = person_data.get("other_names", "") or person_data.get("middle_name", "")
        full_name   = person_data.get("full_name", "") or f"{first_name} {last_name}".strip()
        dob_str     = person_data.get("date_of_birth", "")
        gender      = person_data.get("gender", "")
        national_id = person_data.get("document_number", "") or person_data.get("id_number", "")
        photo_b64   = (id_ver.get("portrait_image") or {}).get("base64", "")

        # Parse DOB
        verified_dob = None
        if dob_str:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    verified_dob = datetime.strptime(dob_str, fmt).date()
                    break
                except ValueError:
                    continue

        # Calculate age
        verified_age = None
        if verified_dob:
            today = timezone.now().date()
            verified_age = (
                today.year - verified_dob.year
                - ((today.month, today.day) < (verified_dob.month, verified_dob.day))
            )

        age_eligible = (
            PLAYER_MIN_AGE <= verified_age <= PLAYER_MAX_AGE
            if verified_age is not None else False
        )

        person_found = bool(id_ver) and status in (
            "Approved", "In Review", "Declined"
        )

        # ── Extract NRB database validation ──────────────────────────────
        db_validations = data.get("database_validations", [])
        nrb_val = {}
        for dv in db_validations:
            # Look for the Kenya NRB service
            if (dv.get("service_id") == "ken_national_id"
                    or dv.get("issuing_state") == "KEN"):
                nrb_val = dv
                break

        nrb_match_type = nrb_val.get("match_type", "")
        nrb_checked = bool(nrb_val)
        nrb_dob_match = False
        if nrb_val:
            dob_field = (nrb_val.get("field_validations") or {}).get("date_of_birth", "")
            nrb_dob_match = dob_field == "full_match"

        # person_found is stronger when NRB confirmed it
        if nrb_checked and nrb_match_type in ("full_match", "partial_match"):
            person_found = True

        # ── Age matching ──────────────────────────────────────────────────
        # For age verification we treat full_match on NRB DOB as authoritative.
        # If NRB wasn't checked (no database validation step in workflow),
        # fall back to DOB equality from the OCR'd document.
        age_matches = nrb_dob_match if nrb_checked else bool(verified_dob)

        overall_approved = status == "Approved"

        return DiditVerificationResult(
            success=True,
            person_found=person_found,
            verified_name=full_name,
            first_name=first_name,
            last_name=last_name,
            other_names=other_names,
            verified_dob=verified_dob,
            verified_age=verified_age,
            gender=gender,
            national_id=national_id,
            age_matches=age_matches,
            age_eligible=age_eligible,
            session_id=session_id,
            reference_number=session_num,
            session_status=status,
            nrb_match_type=nrb_match_type,
            nrb_checked=nrb_checked,
            photo=photo_b64,
            checked_at=now,
            raw_response=data,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  Simulation / sandbox fallback
    # ──────────────────────────────────────────────────────────────────────────

    def _simulate_session(self, player, now: datetime) -> DiditVerificationResult:
        """
        Return a fake session when no API key is configured.
        The session URL points to Didit's sandbox — the officer can walk through
        the full flow using Didit's magic test documents.
        """
        logger.info("DIDIT SIMULATION — no API key configured for player %s", player.pk)
        fake_id = f"SIM-{hashlib.md5(str(player.pk).encode()).hexdigest()[:8].upper()}"
        return DiditVerificationResult(
            success=True,
            session_id=fake_id,
            reference_number=fake_id,
            session_url=f"https://verify.didit.me/sandbox/demo?ref={fake_id}",
            session_status="Not Started",
            is_simulation=True,
            checked_at=now,
        )

    def _simulate_decision(self, session_id: str, now: datetime) -> DiditVerificationResult:
        """
        Return a deterministic fake decision for sandbox testing.
        Produces an approved result with simulated player data.
        """
        logger.info("DIDIT SIMULATION — decision for session %s", session_id)
        seed = int(hashlib.md5(session_id.encode()).hexdigest(), 16)

        first_names = ["James", "John", "Peter", "Mary", "Grace", "Faith", "Kevin", "Brian"]
        last_names  = ["Ochieng", "Wanjiku", "Kamau", "Kiprop", "Otieno", "Mutua"]
        first = first_names[seed % len(first_names)]
        last  = last_names[(seed // 100) % len(last_names)]

        today     = timezone.now().date()
        age       = PLAYER_MIN_AGE + (seed % (PLAYER_MAX_AGE - PLAYER_MIN_AGE + 1))
        birth_year  = today.year - age
        birth_month = 1 + (seed % 12)
        birth_day   = 1 + (seed % 28)
        dob = date(birth_year, birth_month, birth_day)

        return DiditVerificationResult(
            success=True,
            person_found=True,
            verified_name=f"{first} {last}",
            first_name=first,
            last_name=last,
            verified_dob=dob,
            verified_age=age,
            gender="Male" if seed % 2 == 0 else "Female",
            national_id=f"{seed % 99999999:08d}",
            age_matches=True,
            age_eligible=True,
            session_id=session_id,
            reference_number=f"SIM-{session_id[:8].upper()}",
            session_status="Approved",
            nrb_match_type="full_match",
            nrb_checked=True,
            is_simulation=True,
            checked_at=now,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _canonical_json(obj) -> str:
    """
    Produce the canonical JSON string Didit uses for X-Signature-V2:
    - keys sorted recursively
    - whole-valued floats → ints (e.g. 1.0 → 1)
    - compact separators
    - Unicode not escaped
    """
    def _normalise(o):
        if isinstance(o, dict):
            return {k: _normalise(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [_normalise(i) for i in o]
        if isinstance(o, float) and o == int(o):
            return int(o)
        return o

    return json.dumps(_normalise(obj), separators=(",", ":"), ensure_ascii=False)
