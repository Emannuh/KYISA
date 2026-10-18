"""
KYISA — Verifisha Webhook Handler
===================================
Receives report.ready and report.failed events from Verifisha and
updates the corresponding Player's huduma_status field.

Register in Verifisha dashboard → API → Webhooks:
  URL:    https://kyisa.org/api/v1/verifisha/webhook/
  Events: report.ready, report.failed, check.completed, check.failed

Security: verifies X-Verifisha-Signature (HMAC-SHA256) before processing.
          Always check X-Verifisha-Environment to ignore sandbox in production.
"""
import json
import logging

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from teams.verifisha_service import VerifishaService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def verifisha_webhook_view(request):
    """
    Verifisha webhook endpoint.
    Endpoint: POST /api/v1/verifisha/webhook/
    """
    raw_body  = request.body
    signature = request.headers.get("X-Verifisha-Signature", "")
    env       = request.headers.get("X-Verifisha-Environment", "").upper()
    event     = request.headers.get("X-Verifisha-Event", "")
    delivery  = request.headers.get("X-Verifisha-Delivery", "")

    logger.info("Verifisha webhook: event=%s delivery=%s env=%s", event, delivery, env)

    # ── Signature verification ────────────────────────────────────────────────
    svc = VerifishaService()
    if not svc.verify_webhook_signature(raw_body, signature):
        logger.warning("Verifisha webhook: invalid signature from %s",
                       request.META.get("REMOTE_ADDR"))
        return JsonResponse({"error": "Invalid signature"}, status=401)

    # ── Parse payload ─────────────────────────────────────────────────────────
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    lifecycle = payload.get("lifecycle", {})
    terminal  = lifecycle.get("terminal", False)
    event_name = lifecycle.get("event", event)

    # ── Only act on terminal report events ───────────────────────────────────
    if lifecycle.get("resource") != "report" or not terminal:
        # Acknowledge non-terminal or non-report events immediately
        return JsonResponse({"received": True, "action": "ignored"})

    if event_name not in ("report.ready", "report.failed"):
        return JsonResponse({"received": True, "action": "ignored"})

    # ── Extract report_id and find the player ────────────────────────────────
    report_data = payload.get("report", {})
    report_id   = report_data.get("id", "")

    # Try CountyPlayer first (active system), then Player (legacy)
    from teams.verifisha_webhook import _find_county_player_for_report
    county_player = _find_county_player_for_report(payload, report_id)
    if county_player:
        from teams.verifisha_webhook import _apply_verifisha_result_county
        result = svc.parse_webhook_payload(payload)
        _apply_verifisha_result_county(county_player, result, report_id)
        logger.info("Verifisha webhook: CountyPlayer %s → %s", county_player.pk, county_player.huduma_status)
        return JsonResponse({"received": True, "county_player_pk": county_player.pk, "report_id": report_id})

    # Fall back to legacy Player model
    player = _find_player_for_report(payload, report_id)
    if not player:
        logger.warning("Verifisha webhook: no player found for report_id=%s", report_id)
        return JsonResponse({"received": True, "warning": "player not found"})

    # ── Parse the result and apply it ────────────────────────────────────────
    result = svc.parse_webhook_payload(payload)
    _apply_verifisha_result(player, result, report_id)

    logger.info(
        "Verifisha webhook applied: player %s (%s %s) → huduma_status=%s",
        player.pk, player.first_name, player.last_name, player.huduma_status,
    )

    return JsonResponse({"received": True, "player_pk": player.pk, "report_id": report_id})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_player_for_report(payload: dict, report_id: str):
    """Find a Player by Verifisha report_id stored in huduma_reference."""
    from teams.models import Player

    # 1. Look up by report_id stored in huduma_reference
    player = Player.objects.filter(huduma_reference=report_id).first()
    if player:
        return player

    # 2. Try metadata embedded in the report payload
    report  = payload.get("report", {})
    meta    = report.get("metadata", {})
    pk_str  = meta.get("kyisa_player_pk", "")
    if pk_str:
        try:
            player = Player.objects.filter(pk=int(pk_str)).first()
            if player:
                return player
        except (ValueError, TypeError):
            pass

    return None


def _apply_verifisha_result(player, result, report_id: str):
    """
    Write the Verifisha result onto the Player's huduma fields.
    Keeps compatibility with the existing HudumaVerificationStatus choices.
    """
    from teams.models import HudumaVerificationStatus, PlayerVerificationLog, VerificationStep

    risk    = result.risk_level
    status  = result.status

    if status == "COMPLETED" and result.person_found and risk in ("LOW", "MEDIUM"):
        player.huduma_status    = HudumaVerificationStatus.VERIFIED
        player.huduma_reference = report_id
        player.huduma_notes     = (
            f"Verifisha: {result.conclusion_title}. "
            f"Risk: {risk}. "
            f"Name: {result.verified_name or '—'}, "
            f"DOB: {result.verified_dob or '—'}, "
            f"Age: {result.verified_age or '—'}."
        )
    elif status == "PENDING_REVIEW":
        player.huduma_status    = HudumaVerificationStatus.PENDING
        player.huduma_reference = report_id
        player.huduma_notes     = (
            f"Verifisha: report under review. Risk: {risk}. "
            f"Conclusion: {result.conclusion_title}."
        )
    elif status in ("FAILED",) or (status == "COMPLETED" and not result.person_found):
        player.huduma_status    = HudumaVerificationStatus.FAILED
        player.huduma_reference = report_id
        identity = result.identity_check
        flags    = identity.flags if identity else []
        player.huduma_notes = (
            f"Verifisha: {result.conclusion_title or 'Verification failed'}. "
            + (f"Flags: {', '.join(flags)}." if flags else "Person not found in IPRS.")
        )
    elif status == "COMPLETED" and risk in ("HIGH", "CRITICAL"):
        player.huduma_status    = HudumaVerificationStatus.FAILED
        player.huduma_reference = report_id
        identity = result.identity_check
        flags    = identity.flags if identity else []
        player.huduma_notes = (
            f"Verifisha HIGH risk: {result.conclusion_title}. "
            + (f"Flags: {', '.join(flags)}." if flags else "")
        )
    else:
        player.huduma_status    = HudumaVerificationStatus.PENDING
        player.huduma_reference = report_id
        player.huduma_notes     = f"Verifisha: {status} / {risk}. Manual review required."

    player.huduma_verified_at = timezone.now()
    player.save(update_fields=["huduma_status", "huduma_reference", "huduma_notes", "huduma_verified_at"])

    # Audit log
    try:
        PlayerVerificationLog.objects.create(
            player=player,
            step=VerificationStep.HUDUMA,
            action="verifisha_webhook",
            result=player.huduma_status,
            details={
                "report_id": report_id,
                "status": status,
                "risk_level": risk,
                "risk_score": result.risk_score,
                "person_found": result.person_found,
                "verified_name": result.verified_name,
                "verified_dob": str(result.verified_dob) if result.verified_dob else None,
                "flags": result.identity_check.flags if result.identity_check else [],
                "is_simulation": result.is_simulation,
            },
            notes=player.huduma_notes,
            performed_by=None,
        )
    except Exception as exc:
        logger.error("Verifisha webhook: failed to create audit log for player %s: %s", player.pk, exc)


def _apply_verifisha_result_county(player, result, report_id: str):
    """
    Write a Verifisha result onto a CountyPlayer's verifisha_* fields.
    Huduma fields remain separate — they are for manual age verification.
    """
    risk   = result.risk_level
    status = result.status

    if status == "COMPLETED" and result.person_found and risk in ("LOW", "MEDIUM"):
        player.verifisha_status   = "verified"
        player.verifisha_report_id = report_id
        player.verifisha_notes    = (
            f"Verifisha: {result.conclusion_title}. Risk: {risk}. "
            f"Name: {result.verified_name or '—'}, "
            f"DOB: {result.verified_dob or '—'}, "
            f"Age: {result.verified_age or '—'}."
        )
    elif status == "PENDING_REVIEW":
        player.verifisha_status   = "pending"
        player.verifisha_report_id = report_id
        player.verifisha_notes    = f"Verifisha: under review. Risk: {risk}."
    elif status in ("FAILED",) or (status == "COMPLETED" and not result.person_found):
        player.verifisha_status   = "failed"
        player.verifisha_report_id = report_id
        identity = result.identity_check
        flags    = identity.flags if identity else []
        player.verifisha_notes = (
            f"Verifisha: {result.conclusion_title or 'Failed'}. "
            + (f"Flags: {', '.join(flags)}." if flags else "Not found in IPRS.")
        )
    elif status == "COMPLETED" and risk in ("HIGH", "CRITICAL"):
        player.verifisha_status   = "failed"
        player.verifisha_report_id = report_id
        player.verifisha_notes    = f"Verifisha HIGH risk ({risk}): {result.conclusion_title}."
    else:
        player.verifisha_status   = "pending"
        player.verifisha_report_id = report_id
        player.verifisha_notes    = f"Verifisha: {status}/{risk}. Manual review required."

    player.verifisha_checked_at = timezone.now()
    player.save(update_fields=[
        "verifisha_status", "verifisha_report_id",
        "verifisha_notes", "verifisha_checked_at",
    ])


def _find_county_player_for_report(payload: dict, report_id: str):
    """Find a CountyPlayer by report_id stored in huduma_reference."""
    from teams.models import CountyPlayer

    player = CountyPlayer.objects.filter(huduma_reference=report_id).first()
    if player:
        return player

    # Try metadata
    meta   = payload.get("report", {}).get("metadata", {})
    pk_str = meta.get("kyisa_county_player_pk", "")
    if pk_str:
        try:
            return CountyPlayer.objects.filter(pk=int(pk_str)).first()
        except (ValueError, TypeError):
            pass
    return None
