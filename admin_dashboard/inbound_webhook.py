"""
KYISA — Brevo Inbound Email Webhook
====================================
Receives parsed emails from Brevo whenever someone sends to *@reply.kyisa.org.
Brevo POSTs a JSON payload to /api/inbound-email/ and this view stores it
as an EmailLog(direction='IN') for display in the Email Centre inbox.

Setup in Brevo:
  Inbound Parsing → Add Domain → reply.kyisa.org
  Webhook URL: https://kyisa.org/api/inbound-email/

DNS records required in Namecheap for reply.kyisa.org:
  MX  reply  inbound.brevo.com  (priority 10)
  TXT reply  brevo-code:<your-brevo-code>
"""
import json
import logging
import hmac
import hashlib

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def brevo_inbound_webhook(request):
    """
    Receives inbound email events from Brevo inbound parsing.
    Brevo POSTs a JSON body with an 'items' array of parsed emails.
    Each item is stored as an EmailLog(direction='IN').
    """
    # ── Optional signature verification ──────────────────────────────────────
    # If BREVO_WEBHOOK_SECRET is set, verify the X-Brevo-Signature header.
    webhook_secret = getattr(settings, 'BREVO_WEBHOOK_SECRET', '')
    if webhook_secret:
        signature = request.headers.get('X-Brevo-Signature', '')
        expected  = hmac.new(
            webhook_secret.encode(),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning('Brevo inbound webhook: invalid signature')
            return JsonResponse({'error': 'Invalid signature'}, status=403)

    # ── Parse payload ─────────────────────────────────────────────────────────
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        logger.warning('Brevo inbound webhook: invalid JSON body')
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    items = payload if isinstance(payload, list) else payload.get('items', [])

    if not items:
        return JsonResponse({'status': 'ok', 'stored': 0})

    from admin_dashboard.models import EmailLog

    stored = 0
    for item in items:
        try:
            # Extract fields from Brevo's inbound email payload
            message_id  = item.get('MessageId', '').strip()
            subject     = item.get('Subject', '(No Subject)')[:500]
            from_email  = item.get('From', {})
            if isinstance(from_email, dict):
                from_addr = from_email.get('Address', from_email.get('Name', ''))
            else:
                from_addr = str(from_email)

            # Recipients
            to_list = item.get('To', [])
            if isinstance(to_list, list):
                to_addr = ', '.join(
                    r.get('Address', '') if isinstance(r, dict) else str(r)
                    for r in to_list
                )
            else:
                to_addr = str(to_list)

            # Body — Brevo provides TextBody (clean) and HtmlBody
            body_text = item.get('TextBody', '') or item.get('ExtractedMarkdownMessage', '')
            body_html = item.get('HtmlBody', '')

            # Date
            date_str = item.get('SentAtDate', '') or item.get('date', '')
            try:
                from email.utils import parsedate_to_datetime
                received_at = parsedate_to_datetime(date_str)
                if received_at.tzinfo is None:
                    received_at = timezone.make_aware(received_at)
            except Exception:
                received_at = timezone.now()

            # Dedup by message_id
            if message_id and EmailLog.objects.filter(
                message_id=message_id, direction='IN'
            ).exists():
                continue

            EmailLog.objects.create(
                direction  = 'IN',
                status     = 'sent',
                from_email = from_addr[:254],
                to_emails  = to_addr[:500],
                subject    = subject,
                body_text  = str(body_text)[:5000],
                body_html  = str(body_html)[:10000],
                sent_at    = received_at,
                message_id = message_id[:255],
            )
            stored += 1
            logger.info('Inbound email stored: %s from %s', subject, from_addr)

        except Exception as exc:
            logger.error('Brevo inbound webhook: failed to store item: %s', exc)
            continue

    return JsonResponse({'status': 'ok', 'stored': stored})
