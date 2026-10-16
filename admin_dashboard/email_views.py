# admin_dashboard/email_views.py — Email dashboard for system admins
import json
import os
import sys
import subprocess
import threading

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from django.db.models import Q
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
    qs = EmailLog.objects.filter(direction='OUT')

    status    = request.GET.get('status', '')
    search    = request.GET.get('q', '')
    date_from = request.GET.get('from', '')
    date_to   = request.GET.get('to', '')

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

    stats = {
        'total': EmailLog.objects.filter(direction='OUT').count(),
        'sent':  EmailLog.objects.filter(direction='OUT', status='sent').count(),
        'failed': EmailLog.objects.filter(direction='OUT', status='failed').count(),
        'today': EmailLog.objects.filter(direction='OUT', sent_at__date=timezone.now().date()).count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/email_logs.html', {
        'page_obj':     page,
        'stats':        stats,
        'status_filter': status,
        'search_query': search,
        'date_from':    date_from,
        'date_to':      date_to,
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
        to_raw  = request.POST.get('to_emails', '')
        subject = request.POST.get('subject', '').strip()
        body    = request.POST.get('body', '').strip()
        cc_raw  = request.POST.get('cc_emails', '')

        to_list = [e.strip() for e in to_raw.replace(';', ',').split(',') if e.strip()]
        cc_list = [e.strip() for e in cc_raw.replace(';', ',').split(',') if e.strip()]

        if not to_list or not subject or not body:
            messages.error(request, 'Please fill in To, Subject, and Body.')
            return render(request, 'dashboard/email_compose.html', {
                'to_emails': to_raw, 'subject': subject,
                'body': body, 'cc_emails': cc_raw,
            })

        from kyisa_cms.email_utils import _base_html, _send
        html_body = _base_html(subject, f"<p>{body}</p>")
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

    preset    = request.GET.get('preset', '')
    to_emails = ''
    if preset == 'all_managers':
        to_emails = ', '.join(
            User.objects.filter(role='team_manager', is_active=True).values_list('email', flat=True)
        )
    elif preset == 'all_referees':
        to_emails = ', '.join(
            User.objects.filter(role='referee', is_active=True).values_list('email', flat=True)
        )
    elif preset == 'all_admins':
        to_emails = ', '.join(
            User.objects.filter(
                Q(is_superuser=True) | Q(is_staff=True) | Q(role='admin')
            ).values_list('email', flat=True)
        )

    return render(request, 'dashboard/email_compose.html', {
        'to_emails': to_emails,
        'subject':   request.GET.get('subject', ''),
        'reply_to':  request.GET.get('reply_to', ''),
    })


@login_required
@user_passes_test(_is_admin)
def email_resend(request, email_id):
    """Resend a previously failed email."""
    if request.method != 'POST':
        return redirect('email_logs')

    original = get_object_or_404(EmailLog, pk=email_id)
    to_list  = [e.strip() for e in original.to_emails.split(',') if e.strip()]
    cc_list  = [e.strip() for e in original.cc_emails.split(',') if e.strip()] if original.cc_emails else []

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
            direction='OUT', status='sent',
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
    """Send a test email to verify email configuration."""
    if request.method != 'POST':
        return redirect('email_logs')

    recipient = request.POST.get('test_email', request.user.email)
    try:
        from kyisa_cms.email_utils import _base_html
        html = _base_html(
            "KYISA Email Test",
            "<p>This is a test email from the KYISA CMS.</p>"
            "<p>If you received this, your email configuration is working correctly.</p>"
            f"<p><small>Sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} EAT</small></p>",
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
    Trigger the fetch_inbox management command via subprocess.
    The management command connects to IMAP outside the web worker thread,
    so it cannot kill gunicorn on timeout.
    """
    if request.method != 'POST':
        return redirect('email_inbox')

    imap_password = getattr(django_settings, 'IMAP_PASSWORD', '')
    if not imap_password:
        messages.error(request, 'IMAP_PASSWORD is not configured. Add it to Railway variables.')
        return redirect('email_inbox')

    result = {'output': '', 'error': '', 'done': False}

    def _run():
        try:
            # Find manage.py — it sits at the Django BASE_DIR
            base_dir = str(django_settings.BASE_DIR)
            manage_py = os.path.join(base_dir, 'manage.py')
            proc = subprocess.run(
                [sys.executable, manage_py, 'fetch_inbox', '--limit', '100'],
                capture_output=True,
                text=True,
                timeout=55,
            )
            result['output'] = proc.stdout or ''
            result['error']  = proc.stderr or ''
            result['done']   = True
        except subprocess.TimeoutExpired:
            result['error'] = 'timeout'
            result['done']  = True
        except Exception as exc:
            result['error'] = str(exc)
            result['done']  = True

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=58)

    if not result['done']:
        messages.warning(request, 'Inbox fetch is still running in the background — check back in a moment.')
    elif result['error'] == 'timeout':
        messages.warning(request, 'Fetch timed out — inbox may still be processing.')
    elif 'IMAP_PASSWORD' in result.get('error', ''):
        messages.error(request, 'IMAP_PASSWORD is not set on the server.')
    elif result['error'] and not result['output']:
        messages.error(request, f'Fetch error: {result["error"][:300]}')
    else:
        # Parse the summary line from management command output
        for line in result['output'].splitlines():
            if line.strip().startswith('Done —'):
                messages.success(request, f'✓ {line.strip()}')
                break
        else:
            if result['output']:
                messages.success(request, 'Inbox fetched successfully.')
            else:
                messages.info(request, 'No new emails found.')

    return redirect('email_inbox')


@login_required
@user_passes_test(_is_admin)
def email_inbox(request):
    """View incoming emails from it@kyisa.org inbox."""
    qs = EmailLog.objects.filter(direction='IN')

    search    = request.GET.get('q', '')
    date_from = request.GET.get('from', '')
    date_to   = request.GET.get('to', '')

    if search:
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
        'total':  EmailLog.objects.filter(direction='IN').count(),
        'today':  EmailLog.objects.filter(direction='IN', sent_at__date=timezone.now().date()).count(),
        'outbox': EmailLog.objects.filter(direction='OUT', status='sent').count(),
        'failed': EmailLog.objects.filter(direction='OUT', status='failed').count(),
    }

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'dashboard/email_inbox.html', {
        'page_obj':     page,
        'stats':        stats,
        'search_query': search,
        'date_from':    date_from,
        'date_to':      date_to,
    })
