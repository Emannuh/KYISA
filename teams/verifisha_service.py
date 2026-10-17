"""
KYISA — Verifisha Identity Verification Service
=================================================
Integrates with Verifisha (verifisha.com) for Kenya player identity verification.

Verifisha is a consent-led, ODPC-aligned Kenyan KYC platform connecting to:
  IPRS · KRA · NTSA · CRB Bureaus · M-Pesa · BRS · Sanctions & PEP lists

API base: https://api.verifisha.com/api/v1
Docs:     https://docs.verifisha.com

Flow:
  1. POST /api/v1/reports  →  creates report, returns report_id (status: PROCESSING)
  2. Verifisha runs checks asynchronously
  3. Webhook fires → POST /api/v1/verifisha/webhook/ → updates player record

Consent modes:
  CUSTOMER_ATTESTED  — we already have player consent (use for enrolled players)
  VERIFISHA_HOSTED   — Verifisha sends a consent link to the player (use for external)

Configuration (Railway environment variables):
    VERIFISHA_API_KEY=vrf_test_...   or vrf_live_...
    VERIFISHA_WEBHOOK_SECRET=<long random secret>
    VERIFISHA_ENVIRONMENT=sandbox    # 'sandbox' or 'production'

Usage:
    from teams.verifisha_service import VerifishaService
    svc = VerifishaService()
    result = svc.verify_player(player)   # returns VerifishaResult
"""
import hashlib
import hmac
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional

import requests
from django.conf import settings
from django.utils import timezone

from teams.huduma_service import IPRSLookupResult

logger = logging.getLogger(__name__)

# ── Check names used in checksRequested ──────────────────────────────────────
CHECK_IDENTITY          = "IDENTITY"
CHECK_IDENTITY_IMAGE    = "IDENTITY_WITH_IMAGE"
CHECK_LIVENESS          = "LIVENESS_CHECK"
CHECK_AML               = "AML_CHECK"
CHECK_KRA_PIN           = "KRA_PIN"
CHECK_MPESA_KYC         = "MPESA_KYC"

# Default checks for a KYISA player verification
KYISA_PLAYER_CHECKS = [CHECK_IDENTITY]


@dataclass
class VerifishaCheckResult:
    """Result for a single check within a Verifisha report."""
    name: str
    display_name: str = ""
    status: str = ""          # COMPLETED, FAILED, PENDING, RUNNING, SKIPPED
    risk_level: str = ""      # LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
    risk_score: Optional[int] = None
    summary: str = ""
    headline: str = ""
    flags: List[str] = field(default_factory=list)
    evidence: List[dict] = field(default_factory=list)   # [{key, label, value}]
    executed_at: Optional[str] = None

    @property
    def is_clear(self) -> bool:
        return self.status == "COMPLETED" and self.risk_level in ("LOW",) and not self.flags

    @property
    def is_failed_execution(self) -> bool:
        """Execution error — not an adverse finding about the subject."""
        return self.status == "FAILED"

    def get_evidence_value(self, key: str) -> str:
        """Look up a specific evidence key (e.g. 'result.Date of birth')."""
        for item in self.evidence:
            if item.get("key") == key:
                return item.get("value", "")
        return ""


@dataclass
class VerifishaResult:
    """Full result from a Verifisha report."""
    success: bool
    report_id: str = ""
    status: str = ""             # PROCESSING, COMPLETED, FAILED, PENDING_REVIEW
    risk_level: str = ""         # LOW, MEDIUM, HIGH, CRITICAL, UNKNOWN
    risk_score: Optional[int] = None
    consent_status: str = ""
    conclusion_title: str = ""
    conclusion_description: str = ""
    checks: List[VerifishaCheckResult] = field(default_factory=list)
    error_message: str = ""
    is_simulation: bool = False

    # Parsed identity fields (from IDENTITY check evidence)
    person_found: bool = False
    verified_name: str = ""
    verified_dob: Optional[date] = None
    verified_age: Optional[int] = None
    gender: str = ""
    citizenship: str = ""
    national_id: str = ""

    @property
    def identity_check(self) -> Optional[VerifishaCheckResult]:
        for c in self.checks:
            if c.name in (CHECK_IDENTITY, CHECK_IDENTITY_IMAGE):
                return c
        return None

    @property
    def is_identity_clear(self) -> bool:
        c = self.identity_check
        return c is not None and c.is_clear

    @property
    def is_processing(self) -> bool:
        return self.status == "PROCESSING"

    @property
    def is_complete(self) -> bool:
        return self.status in ("COMPLETED", "PENDING_REVIEW", "FAILED")

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "report_id": self.report_id,
            "status": self.status,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "person_found": self.person_found,
            "verified_name": self.verified_name,
            "verified_dob": self.verified_dob.isoformat() if self.verified_dob else None,
            "verified_age": self.verified_age,
            "gender": self.gender,
            "citizenship": self.citizenship,
            "national_id": self.national_id,
            "consent_status": self.consent_status,
            "conclusion": self.conclusion_title,
            "error_message": self.error_message,
            "is_simulation": self.is_simulation,
        }


class VerifishaService:
    """
    Verifisha Kenya identity verification service.

    Produces VerifishaResult — also updates IPRSLookupResult for backward
    compatibility with existing huduma_status player fields.

    Sandbox:    vrf_test_ key  — no charges, same host
    Production: vrf_live_ key  — issued after business KYB approval
    """

    BASE_URL = "https://api.verifisha.com/api/v1"

    def __init__(self):
        self.api_key     = getattr(settings, 'VERIFISHA_API_KEY', '')
        self.environment = getattr(settings, 'VERIFISHA_ENVIRONMENT', 'sandbox')
        self.webhook_secret = getattr(settings, 'VERIFISHA_WEBHOOK_SECRET', '')
        self.timeout     = 30
        self._is_sandbox = self.api_key.startswith('vrf_test_')
        self._is_live    = self.api_key.startswith('vrf_live_')

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ──────────────────────────────────────────────────────────────────────────
    #  Public API
    # ──────────────────────────────────────────────────────────────────────────

    def verify_player(self, player, checks: List[str] = None) -> VerifishaResult:
        """
        Submit a Verifisha report for a KYISA player.

        Uses CUSTOMER_ATTESTED consent (player enrolled and consented at
        registration). Returns a VerifishaResult — status will be PROCESSING
        until the webhook fires.

        Args:
            player: teams.Player instance
            checks: list of check names; defaults to [IDENTITY]
        """
        if not self.api_key:
            logger.warning("VERIFISHA_API_KEY not set — using simulation mode.")
            return self._simulate(player)

        checks = checks or KYISA_PLAYER_CHECKS
        idempotency_key = f"kyisa-player-{player.pk}-{'-'.join(checks)}"

        payload = {
            "reports": [{
                "subject": {
                    "subjectType": "INDIVIDUAL",
                    "fullName": player.get_full_name() if hasattr(player, 'get_full_name') else
                                f"{player.first_name} {player.last_name}",
                    "idNumber": str(player.national_id_number or ""),
                    "country": "KE",
                },
                "checksRequested": checks,
                "purpose": "KYISA player eligibility verification",
                "consent": {
                    "mode": "CUSTOMER_ATTESTED",
                    "attestation": {
                        "method": "TERMS_AND_CONDITIONS",
                        "capturedAt": timezone.now().isoformat(),
                    }
                },
                "paymentMode": "SELF",
                "metadata": {
                    "kyisa_player_pk": str(player.pk),
                    "kyisa_player_name": f"{player.first_name} {player.last_name}",
                },
            }]
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/reports",
                json=payload,
                headers={**self._headers, "Idempotency-Key": idempotency_key},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.Timeout:
            logger.error("Verifisha timeout for player %s", player.pk)
            return VerifishaResult(success=False, error_message="Request timed out. Please try again.")
        except requests.exceptions.HTTPError as exc:
            sc = exc.response.status_code if exc.response else 0
            try:
                body = exc.response.json()
                msg = body.get("title", body.get("detail", str(exc)))
                error_code = body.get("errorCode", "")
            except Exception:
                msg, error_code = str(exc), ""
            logger.error("Verifisha HTTP %s for player %s: %s (%s)", sc, player.pk, msg, error_code)
            return VerifishaResult(success=False, error_message=f"Verification service error ({sc}): {msg}")
        except requests.exceptions.RequestException as exc:
            logger.exception("Verifisha network error for player %s", player.pk)
            return VerifishaResult(success=False, error_message=f"Network error: {exc}")

        # API returns an array of reports
        reports = data if isinstance(data, list) else data.get("reports", [data])
        if not reports:
            return VerifishaResult(success=False, error_message="No report returned by Verifisha.")

        report = reports[0]
        report_id = report.get("id") or report.get("reportId", "")
        status    = report.get("status", "PROCESSING")
        is_sandbox = resp.headers.get("X-Verifisha-Sandbox", "").lower() == "true"

        logger.info("Verifisha report created — player %s, report_id=%s, status=%s, sandbox=%s",
                    player.pk, report_id, status, is_sandbox)

        return VerifishaResult(
            success=True,
            report_id=report_id,
            status=status,
            is_simulation=is_sandbox,
            consent_status=report.get("consentStatus", ""),
        )

    def get_report(self, report_id: str) -> VerifishaResult:
        """Fetch a completed report by ID."""
        if not self.api_key:
            return VerifishaResult(success=False, error_message="No API key configured.")
        try:
            resp = requests.get(
                f"{self.BASE_URL}/reports/{report_id}",
                headers=self._headers,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return self._parse_report(resp.json())
        except requests.exceptions.RequestException as exc:
            logger.exception("Verifisha get_report error: %s", exc)
            return VerifishaResult(success=False, error_message=str(exc))

    def lookup_by_national_id(self, national_id: str) -> IPRSLookupResult:
        """
        Synchronous IPRS lookup compatible with the existing IPRSLookupResult interface.
        Submits a report and immediately polls for the result (use only in admin contexts
        where the IDENTITY check resolves quickly in sandbox).
        """
        if not self.api_key:
            return self._simulate_iprs(national_id)

        payload = {
            "reports": [{
                "subject": {
                    "subjectType": "INDIVIDUAL",
                    "idNumber": national_id.strip(),
                    "country": "KE",
                },
                "checksRequested": [CHECK_IDENTITY],
                "purpose": "KYISA IPRS lookup",
                "consent": {"mode": "CUSTOMER_ATTESTED",
                             "attestation": {"method": "TERMS_AND_CONDITIONS",
                                             "capturedAt": timezone.now().isoformat()}},
                "paymentMode": "SELF",
            }]
        }
        idempotency = f"kyisa-iprs-{national_id}-{uuid.uuid4().hex[:8]}"
        try:
            resp = requests.post(
                f"{self.BASE_URL}/reports",
                json=payload,
                headers={**self._headers, "Idempotency-Key": idempotency},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            reports = resp.json()
            reports = reports if isinstance(reports, list) else reports.get("reports", [reports])
            report_id = reports[0].get("id") or reports[0].get("reportId", "")
        except Exception as exc:
            logger.exception("Verifisha lookup error for ID %s", national_id)
            return IPRSLookupResult(success=False, error_message=str(exc))

        # Poll up to 10s for sandbox (usually resolves in ~2s)
        import time
        for _ in range(5):
            time.sleep(2)
            result = self.get_report(report_id)
            if result.is_complete:
                break

        if not result.person_found and not result.success:
            return IPRSLookupResult(success=False, error_message=result.error_message)

        return IPRSLookupResult(
            success=result.success,
            person_found=result.person_found,
            full_name=result.verified_name,
            first_name=result.verified_name.split()[0] if result.verified_name else "",
            last_name=" ".join(result.verified_name.split()[1:]) if result.verified_name else "",
            date_of_birth=result.verified_dob,
            age=result.verified_age,
            gender=result.gender,
            national_id=result.national_id or national_id,
            reference_number=result.report_id,
            is_simulation=result.is_simulation,
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  Webhook signature verification
    # ──────────────────────────────────────────────────────────────────────────

    def verify_webhook_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify X-Verifisha-Signature against the raw request body.
        Uses HMAC-SHA256 with the VERIFISHA_WEBHOOK_SECRET.
        """
        if not self.webhook_secret:
            logger.warning("VERIFISHA_WEBHOOK_SECRET not set — skipping signature check")
            return True  # Fail-open in dev; tighten in production

        try:
            expected = hmac.new(
                self.webhook_secret.encode("utf-8"),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature_header or "")
        except Exception:
            logger.exception("Verifisha webhook signature verification failed")
            return False

    def parse_webhook_payload(self, payload: dict) -> VerifishaResult:
        """Parse an incoming Verifisha webhook payload into a VerifishaResult."""
        report_data = payload.get("report", {})
        checks_data = payload.get("checks", [])
        environment = payload.get("environment", "")

        result = self._parse_report_data(report_data, checks_data)
        result.is_simulation = environment.upper() == "SANDBOX"
        return result

    # ──────────────────────────────────────────────────────────────────────────
    #  Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_report(self, data: dict) -> VerifishaResult:
        """Parse a GET /reports/{id} response."""
        checks_data = data.get("checks", [])
        is_sandbox = data.get("environment", "").upper() == "SANDBOX"
        result = self._parse_report_data(data, checks_data)
        result.is_simulation = is_sandbox
        return result

    def _parse_report_data(self, report: dict, checks_data: list) -> VerifishaResult:
        """Common parser for both GET response and webhook payload."""
        report_id = report.get("id") or report.get("reportId", "")
        status    = report.get("status", "")
        risk_level = report.get("riskLevel", "")
        risk_score = report.get("compositeScore")
        consent    = report.get("consentStatus", "")
        conclusion = report.get("conclusion", {})

        checks = [self._parse_check(c) for c in checks_data]

        result = VerifishaResult(
            success=True,
            report_id=report_id,
            status=status,
            risk_level=risk_level,
            risk_score=risk_score,
            consent_status=consent,
            conclusion_title=conclusion.get("title", ""),
            conclusion_description=conclusion.get("description", ""),
            checks=checks,
        )

        # Extract identity fields from IDENTITY check evidence
        identity = result.identity_check
        if identity and identity.status == "COMPLETED":
            result.person_found = True

            # Try displaySections first (richer data)
            dob_str = identity.get_evidence_value("result.Date of birth") or \
                      identity.get_evidence_value("dateOfBirth") or ""
            result.citizenship = identity.get_evidence_value("result.Citizenship") or \
                                 identity.get_evidence_value("citizenship") or ""
            result.national_id = identity.get_evidence_value("result.ID number") or \
                                 identity.get_evidence_value("idNumber") or ""

            # Parse DOB
            if dob_str:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        dob = datetime.strptime(str(dob_str), fmt).date()
                        result.verified_dob = dob
                        today = timezone.now().date()
                        result.verified_age = today.year - dob.year - (
                            (today.month, today.day) < (dob.month, dob.day)
                        )
                        break
                    except (ValueError, TypeError):
                        continue

        elif identity and identity.status == "FAILED":
            result.person_found = False

        return result

    def _parse_check(self, data: dict) -> VerifishaCheckResult:
        """Parse a single check entry."""
        return VerifishaCheckResult(
            name=data.get("name", ""),
            display_name=data.get("displayName", ""),
            status=data.get("status", ""),
            risk_level=data.get("riskLevel", ""),
            risk_score=data.get("riskScore"),
            summary=data.get("summary", ""),
            headline=data.get("headline", ""),
            flags=data.get("flags", []),
            evidence=data.get("evidenceDetails", []),
            executed_at=data.get("executedAt"),
        )

    # ──────────────────────────────────────────────────────────────────────────
    #  Simulation fallback (no API key)
    # ──────────────────────────────────────────────────────────────────────────

    def _simulate(self, player) -> VerifishaResult:
        """Deterministic simulation when VERIFISHA_API_KEY is not set."""
        logger.info("Verifisha SIMULATION mode — player %s", player.pk)
        name = f"{player.first_name} {player.last_name}"
        return VerifishaResult(
            success=True,
            report_id=f"sim_rep_{player.pk}",
            status="PROCESSING",
            is_simulation=True,
            conclusion_title="Simulation",
            conclusion_description="No API key — report is simulated.",
        )

    def _simulate_iprs(self, national_id: str) -> IPRSLookupResult:
        """Simulation fallback for lookup_by_national_id."""
        import hashlib as _h
        logger.info("Verifisha SIMULATION IPRS — ID %s", national_id)
        h = int(_h.md5(national_id.encode()).hexdigest(), 16)
        names = ["James Ochieng", "Grace Wanjiku", "Peter Mwangi",
                 "Mary Chebet", "Brian Otieno", "Faith Kamau"]
        full_name = names[h % len(names)]
        parts = full_name.split()
        today = timezone.now().date()
        age = 18 + (h % 6)
        dob = today.replace(year=today.year - age)
        return IPRSLookupResult(
            success=True,
            person_found=True,
            first_name=parts[0],
            last_name=parts[1] if len(parts) > 1 else "",
            full_name=full_name,
            date_of_birth=dob,
            age=age,
            gender="Male" if h % 2 == 0 else "Female",
            national_id=national_id,
            reference_number=f"sim_{national_id}",
            is_simulation=True,
        )
