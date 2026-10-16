# admin_dashboard/email_views.py — Email dashboard for system admins
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse

from accounts.models import User
from .models import EmailLog


def _is_admin(user):
    return user.is_superuser or user.is_staff or user.role in ('admin', 'secretary_general')


@login_required
@user_passes_test(_is_admin)
def email_logs(request):
    """View all sent/failed system emails with search & filters."""
    qs = EmailLog.objects.all()

    # Filters
    status = request.GET.get('status', '')
    search = request.GET.get('q', '')
    date_from = request.GET.get('from', '')
    date_to = request.GET.get('to', '')

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(subject__icontains=search) |
            Q(to_emails__icontains=search) |
            Q(from_email__icontains=search)
        )
    if date_from:
        qs = qs.filter(sent_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(sent_at__date__lte=date_to)

    # Stats
    stats = {
        'total': EmailLog.objects.count(),
        'sent': EmailLog.objects.filter(status='sent').count(),
        'failed': EmailLog.objects.filter(status='failed').count(),
        'today': EmailLog.objects.filter(sent_at__date=timezone.now().date()).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/email_logs.html', {
        'page_obj': page,
        'stats': stats,
        'status_filter': status,
        'search_query': search,
        'date_from': date_from,
        'date_to': date_to,
    })


@login_required
@user_passes_test(_is_admin)
def email_detail(request, email_id):
    """View a single email's full details."""
    email = get_object_or_404(EmailLog, pk=email_id)
    return render(request, 'dashboard/email_detail.html', {'email': email})


@login_required
@user_passes_test(_is_admin)
def email_compose(request):
    """Compose and send an email from the dashboard."""
    if request.method == 'POST':
        to_raw = request.POST.get('to_emails', '')
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        cc_raw = request.POST.get('cc_emails', '')

        # Parse recipients
        to_list = [e.strip() for e in to_raw.replace(';', ',').split(',') if e.strip()]
        cc_list = [e.strip() for e in cc_raw.replace(';', ',').split(',') if e.strip()]

        if not to_list or not subject or not body:
            messages.error(request, 'Please fill in To, Subject, and Body.')
            return render(request, 'dashboard/email_compose.html', {
                'to_emails': to_raw, 'subject': subject, 'body': body,
                'cc_emails': cc_raw,
            })

        # Build branded HTML
        from kyisa_cms.email_utils import _base_html, _send
        html_body = _base_html(subject, f"<p>{body}</p>")

        # Use background-threaded send (won't crash the worker on timeout)
        _send(
            subject=subject,
            html_body=html_body,
            recipients=to_list,
            cc=cc_list if cc_list else None,
            sent_by=request.user,
            fail_silently=False,
        )
        messages.success(request, f'Email queued for delivery to {", ".join(to_list)}.')
        return redirect('email_logs')

    # GET — show compose form with optional recipient presets
    preset = request.GET.get('preset', '')
    to_emails = ''
    if preset == 'all_managers':
        to_emails = ', '.join(
            User.objects.filter(role='team_manager', is_active=True)
            .values_list('email', flat=True)
        )
    elif preset == 'all_referees':
        to_emails = ', '.join(
            User.objects.filter(role='referee', is_active=True)
            .values_list('email', flat=True)
        )
    elif preset == 'all_admins':
        to_emails = ', '.join(
            User.objects.filter(
                Q(is_superuser=True) | Q(is_staff=True) | Q(role='admin')
            ).values_list('email', flat=True)
        )

    return render(request, 'dashboard/email_compose.html', {
        'to_emails': to_emails,
        'subject': request.GET.get('subject', ''),
        'reply_to': request.GET.get('reply_to', ''),
    })


@login_required
@user_passes_test(_is_admin)
def email_resend(request, email_id):
    """Resend a previously failed email."""
    if request.method != 'POST':
        return redirect('email_logs')

    original = get_object_or_404(EmailLog, pk=email_id)
    to_list = [e.strip() for e in original.to_emails.split(',') if e.strip()]
    cc_list = [e.strip() for e in original.cc_emails.split(',') if e.strip()] if original.cc_emails else []

    try:
        msg = EmailMultiAlternatives(
            subject=original.subject,
            body=original.body_text,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=to_list,
            cc=cc_list if cc_list else None,
        )
        if original.body_html:
            msg.attach_alternative(original.body_html, "text/html")
        msg.send(fail_silently=False)

        EmailLog.objects.create(
            direction='OUT',
            status='sent',
            from_email=original.from_email,
            to_emails=original.to_emails,
            cc_emails=original.cc_emails,
            subject=f"[Resend] {original.subject}",
            body_text=original.body_text,
            body_html=original.body_html,
            sent_by=request.user,
        )
        messages.success(request, 'Email resent successfully.')
    except Exception as e:
        messages.error(request, f'Resend failed: {e}')

    return redirect('email_logs')


@login_required
@user_passes_test(_is_admin)
def test_email(request):
    """Send a test email to verify SES/SMTP configuration."""
    if request.method != 'POST':
        return redirect('email_logs')

    recipient = request.POST.get('test_email', request.user.email)
    try:
        from kyisa_cms.email_utils import _base_html
        html = _base_html(
            "<p>This is a test email from the KYISA CMS.</p>"
            "<p>If you received this, your email configuration is working correctly.</p>"
            f"<p><small>Sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} EAT</small></p>",
            "KYISA Email Test"
        )
        msg = EmailMultiAlternatives(
            subject='[KYISA] Email Configuration Test',
            body='Test email from KYISA CMS. Email is working.',
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)

        EmailLog.objects.create(
            direction='OUT', status='sent',
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to_emails=recipient,
            subject='[KYISA] Email Configuration Test',
            body_text='Test email from KYISA CMS.',
            body_html=html,
            sent_by=request.user,
        )
        messages.success(request, f'Test email sent to {recipient}.')
    except Exception as e:
        messages.error(request, f'Test email failed: {e}')

    return redirect('email_logs')


@login_required
@user_passes_test(_is_admin)
def fetch_inbox(request):
    """
    Fetch unseen emails from it@kyisa.org via IMAP and store them
    as EmailLog records with direction='IN'.
    """
    if request.method != 'POST':
        return redirect('email_inbox')

    import imaplib
    import email as email_lib
    import email.header
    import email.utils
    from django.conf import settings as django_settings

    imap_host     = getattr(django_settings, 'IMAP_HOST',     'mail.privateemail.com')
    imap_port     = int(getattr(django_settings, 'IMAP_PORT', 993))
    imap_user     = getattr(django_settings, 'IMAP_USER',     'it@kyisa.org')
    imap_password = getattr(django_settings, 'IMAP_PASSWORD', '')

    if not imap_password:
        messages.error(request, 'IMAP_PASSWORD is not configured. Add it to Railway variables.')
        return redirect('email_inbox')

    fetched = 0
    skipped = 0
    errors  = 0

    try:
        mail = imaplib.IMAP4_SSL(imap_host, imap_port)
        mail.login(imap_user, imap_password)
        mail.select('INBOX')

        # Fetch all unseen messages
        status, data = mail.search(None, 'UNSEEN')
        if status != 'OK':
            messages.error(request, 'Failed to search inbox.')
            mail.logout()
            return redirect('email_inbox')

        uid_list = data[0].split()
        for uid in uid_list:
            try:
                status, msg_data = mail.fetch(uid, '(RFC822)')
                if status != 'OK':
                    errors += 1
                    continue

                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)

                # Decode subject
                raw_subject = msg.get('Subject', '(No Subject)')
                decoded_parts = email.header.decode_header(raw_subject)
                subject = ''
                for part, enc in decoded_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(enc or 'utf-8', errors='replace')
                    else:
                        subject += part

                # Parse sender and recipients
                from_addr   = email.utils.parseaddr(msg.get('From', ''))[1]
                to_addr     = msg.get('To', imap_user)
                message_id  = msg.get('Message-ID', '').strip()
                date_str    = msg.get('Date', '')

                # Parse date
                from email.utils import parsedate_to_datetime
                try:
                    received_at = parsedate_to_datetime(date_str)
                    from django.utils import timezone as tz
                    if received_at.tzinfo is None:
                        received_at = tz.make_aware(received_at)
                except Exception:
                    from django.utils import timezone as tz
                    received_at = tz.now()

                # Skip if already stored (dedup by message_id)
                if message_id and EmailLog.objects.filter(message_id=message_id, direction='IN').exists():
                    skipped += 1
                    continue

                # Extract body
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
                        body_text = payload.decode(charset, errors='replace')

                EmailLog.objects.create(
                    direction   = 'IN',
                    status      = 'sent',
                    from_email  = from_addr,
                    to_emails   = to_addr,
                    subject     = subject[:500],
                    body_text   = body_text[:5000],
                    body_html   = body_html[:10000],
                    sent_at     = received_at,
                    message_id  = message_id[:255],
                )
                fetched += 1

            except Exception as e:
                errors += 1
                continue

        mail.logout()

    except imaplib.IMAP4.error as e:
        messages.error(request, f'IMAP connection failed: {e}')
        return redirect('email_inbox')
    except Exception as e:
        messages.error(request, f'Unexpected error: {e}')
        return redirect('email_inbox')

    if fetched:
        messages.success(request, f'Fetched {fetched} new email{"s" if fetched != 1 else ""} from it@kyisa.org.')
    elif skipped:
        messages.info(request, f'No new emails — {skipped} already imported.')
    else:
        messages.info(request, 'No new emails in inbox.')

    if errors:
        messages.warning(request, f'{errors} email{"s" if errors != 1 else ""} could not be imported.')

    return redirect('email_inbox')


@login_required
@user_passes_test(_is_admin)
def email_inbox(request):
    """View incoming emails fetched from it@kyisa.org IMAP inbox."""
    qs = EmailLog.objects.filter(direction='IN')

    # Filters
    search    = request.GET.get('q', '')
    date_from = request.GET.get('from', '')
    date_to   = request.GET.get('to', '')

    if search:
        from django.db.models import Q
        qs = qs.filter(
            Q(subject__icontains=search) |
            Q(from_email__icontains=search) |
            Q(body_text__icontains=search)
        )
    if date_from:
        qs = qs.filter(sent_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(sent_at__date__lte=date_to)

    stats = {
        'total':   EmailLog.objects.filter(direction='IN').count(),
        'today':   EmailLog.objects.filter(direction='IN', sent_at__date=timezone.now().date()).count(),
        'outbox':  EmailLog.objects.filter(direction='OUT', status='sent').count(),
        'failed':  EmailLog.objects.filter(direction='OUT', status='failed').count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/email_inbox.html', {
        'page_obj':    page,
        'stats':       stats,
        'search_query': search,
        'date_from':   date_from,
        'date_to':     date_to,
    })
