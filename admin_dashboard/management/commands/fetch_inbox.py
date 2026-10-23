"""
Management command: fetch_inbox
================================
Fetches unseen emails from it@kyisa.org via IMAP SSL and stores them
as EmailLog(direction='IN') records in the database.

Designed to run as a Railway Cron job every 2 minutes:
  python manage.py fetch_inbox

Railway Cron setup:
  Command: python manage.py fetch_inbox
  Schedule: */2 * * * *   (every 2 minutes)

Required Railway environment variables:
  IMAP_HOST      = mail.privateemail.com
  IMAP_PORT      = 993
  IMAP_USER      = it@kyisa.org
  IMAP_PASSWORD  = <mailbox password>
"""
import imaplib
import email as email_lib
import email.header
import email.utils
from email.utils import parsedate_to_datetime

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Fetch unseen emails from it@kyisa.org IMAP inbox into EmailLog'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Fetch ALL emails (not just unseen). Useful for initial import.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of emails to fetch per run (default: 50)',
        )

    def handle(self, *args, **options):
        from admin_dashboard.models import EmailLog

        imap_host     = getattr(settings, 'IMAP_HOST',     'mail.privateemail.com')
        imap_port     = int(getattr(settings, 'IMAP_PORT', 993))
        imap_user     = getattr(settings, 'IMAP_USER',     'it@kyisa.org')
        imap_password = getattr(settings, 'IMAP_PASSWORD', '')

        if not imap_password:
            self.stderr.write(self.style.ERROR(
                'IMAP_PASSWORD is not set. Add it to Railway environment variables.'
            ))
            return

        fetched = 0
        skipped = 0
        errors  = 0
        limit   = options['limit']
        fetch_all = options['all']

        try:
            self.stdout.write(f'Connecting to {imap_host}:{imap_port} as {imap_user}...')
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(imap_user, imap_password)
            mail.select('INBOX')
            self.stdout.write(self.style.SUCCESS('Connected to IMAP server.'))

            # Search for unseen or all emails
            search_criteria = 'ALL' if fetch_all else 'UNSEEN'
            status, data = mail.search(None, search_criteria)
            if status != 'OK':
                self.stderr.write(self.style.ERROR('Failed to search inbox.'))
                mail.logout()
                return

            uid_list = data[0].split()
            total = len(uid_list)
            self.stdout.write(f'Found {total} {search_criteria.lower()} email(s).')

            # Process newest first, up to limit
            uid_list = uid_list[-limit:]

            for uid in uid_list:
                try:
                    status, msg_data = mail.fetch(uid, '(RFC822)')
                    if status != 'OK' or not msg_data or msg_data[0] is None:
                        errors += 1
                        continue

                    raw = msg_data[0][1]
                    if not isinstance(raw, bytes):
                        errors += 1
                        continue

                    msg = email_lib.message_from_bytes(raw)

                    # ── Subject ───────────────────────────────────────────────
                    raw_subject = msg.get('Subject', '(No Subject)')
                    decoded_parts = email.header.decode_header(raw_subject)
                    subject = ''
                    for part, enc in decoded_parts:
                        if isinstance(part, bytes):
                            subject += part.decode(enc or 'utf-8', errors='replace')
                        else:
                            subject += str(part)

                    # ── From / To ─────────────────────────────────────────────
                    from_raw  = msg.get('From', '')
                    from_name, from_addr = email.utils.parseaddr(from_raw)
                    from_display = f'{from_name} <{from_addr}>' if from_name else from_addr

                    to_addr    = msg.get('To', imap_user)
                    message_id = msg.get('Message-ID', '').strip()
                    date_str   = msg.get('Date', '')

                    # ── Date ──────────────────────────────────────────────────
                    try:
                        received_at = parsedate_to_datetime(date_str)
                        if received_at.tzinfo is None:
                            received_at = timezone.make_aware(received_at)
                    except Exception:
                        received_at = timezone.now()

                    # ── Dedup by Message-ID ───────────────────────────────────
                    if message_id and EmailLog.objects.filter(
                        message_id=message_id, direction='IN'
                    ).exists():
                        skipped += 1
                        continue

                    # ── Extract body ──────────────────────────────────────────
                    body_text = ''
                    body_html = ''

                    if msg.is_multipart():
                        for part in msg.walk():
                            ctype = part.get_content_type()
                            disp  = str(part.get('Content-Disposition', ''))
                            if 'attachment' in disp:
                                continue
                            payload = part.get_payload(decode=True)
                            if payload is None:
                                continue
                            charset = part.get_content_charset() or 'utf-8'
                            decoded = payload.decode(charset, errors='replace')
                            if ctype == 'text/plain' and not body_text:
                                body_text = decoded
                            elif ctype == 'text/html' and not body_html:
                                body_html = decoded
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            charset   = msg.get_content_charset() or 'utf-8'
                            decoded   = payload.decode(charset, errors='replace')
                            ctype     = msg.get_content_type()
                            if ctype == 'text/html':
                                body_html = decoded
                            else:
                                body_text = decoded

                    # If we only got HTML, generate a plain text version
                    if body_html and not body_text:
                        from django.utils.html import strip_tags
                        body_text = strip_tags(body_html)

                    # If we only got plain text, wrap it in simple HTML
                    if body_text and not body_html:
                        body_html = f'<pre style="white-space:pre-wrap;font-family:inherit">{body_text}</pre>'

                    # ── Store ─────────────────────────────────────────────────
                    EmailLog.objects.create(
                        direction  = 'IN',
                        status     = 'sent',
                        from_email = from_display[:254],
                        to_emails  = to_addr[:500],
                        subject    = subject[:500],
                        body_text  = body_text,
                        body_html  = body_html,
                        sent_at    = received_at,
                        message_id = message_id[:255],
                    )
                    fetched += 1
                    self.stdout.write(f'  ✓ Stored: {subject[:60]}')

                except Exception as exc:
                    errors += 1
                    self.stderr.write(f'  ✗ Error processing email: {exc}')
                    continue

            mail.logout()

        except imaplib.IMAP4.error as exc:
            self.stderr.write(self.style.ERROR(f'IMAP error: {exc}'))
            return
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'Unexpected error: {exc}'))
            return

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS(
            f'\nDone — fetched: {fetched}, skipped (already stored): {skipped}, errors: {errors}'
        ))
