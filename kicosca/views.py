"""
KICOSCA — Views
================
County Sports Director manages KICOSCA players via a dedicated portal
section completely separate from the KYISA discipline/player flow.

URL prefix: /portal/kicosca/
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from functools import wraps

from .models import (
    KicoscaEdition, KicoscaCountyEntry, KicoscaDiscipline,
    KicoscaPlayer, KicoscaSport, KICOSCA_SQUAD_LIMITS, EmploymentStatus,
)
from .forms import KicoscaPlayerForm


# ── Role guard ────────────────────────────────────────────────────────────────
def kicosca_required(view):
    """Allow KICOSCA Sports Officers and admins/superusers to access KICOSCA portal."""
    @wraps(view)
    @login_required(login_url='web_login')
    def wrapper(request, *args, **kwargs):
        allowed = ('kicosca_officer', 'admin', 'competition_manager', 'secretary_general')
        if request.user.role not in allowed and not request.user.is_superuser:
            messages.error(request, 'You do not have access to the KICOSCA portal.')
            return redirect('dashboard')
        return view(request, *args, **kwargs)
    return wrapper

# Keep old name as alias so existing decorators don't break during transition
county_director_required = kicosca_required


def _get_reg(request):
    """
    For KICOSCA officers, return the CountyRegistration linked to their county field.
    For county directors (legacy), return their own registration.
    Falls back to None if not found.
    """
    from teams.models import CountyRegistration
    # KICOSCA officer — match by county name stored on their user account
    if request.user.role == 'kicosca_officer' and request.user.county:
        return CountyRegistration.objects.filter(
            county=request.user.county, status='approved'
        ).first()
    # Legacy county director
    return CountyRegistration.objects.filter(user=request.user).first()


def _get_or_create_entry(reg, edition):
    """Get or create a KicoscaCountyEntry for this county/edition."""
    entry, _ = KicoscaCountyEntry.objects.get_or_create(
        edition=edition,
        county_registration=reg,
    )
    return entry


# ── Dashboard ─────────────────────────────────────────────────────────────────

@kicosca_required
def kicosca_dashboard(request):
    """KICOSCA home for the KICOSCA Sports Officer (or county director)."""
    reg = _get_reg(request)

    # KICOSCA officer with no matching county registration — show setup message
    # but don't redirect to KYISA county registration (wrong system)
    if not reg and request.user.role == 'kicosca_officer':
        edition = KicoscaEdition.get_active()
        return render(request, 'kicosca/dashboard.html', {
            'reg': None,
            'edition': edition,
            'entry': None,
            'disciplines': [],
            'total_players': 0,
            'verified_count': 0,
            'available_sports': list(KicoscaSport.choices),
            'no_county_setup': True,
        })

    if not reg:
        messages.info(request, 'Please complete your KYISA county registration first.')
        return redirect('county_admin_complete_registration')

    edition = KicoscaEdition.get_active()
    entry   = None
    disciplines = []

    if edition:
        entry = KicoscaCountyEntry.objects.filter(
            edition=edition, county_registration=reg
        ).first()
        if entry:
            disciplines = entry.disciplines.prefetch_related('players').all()

    total_players  = sum(d.player_count for d in disciplines)
    verified_count = sum(
        d.players.filter(verification_status='verified').count()
        for d in disciplines
    )

    return render(request, 'kicosca/dashboard.html', {
        'reg':            reg,
        'edition':        edition,
        'entry':          entry,
        'disciplines':    disciplines,
        'total_players':  total_players,
        'verified_count': verified_count,
        'available_sports': list(KicoscaSport.choices),
    })


# ── Join / Create County Entry ─────────────────────────────────────────────────

@kicosca_required
def kicosca_join(request):
    """County director registers their county into the active KICOSCA edition."""
    reg = _get_reg(request)
    if not reg or not reg.is_approved:
        messages.error(request, 'Your KYISA county registration must be approved first.')
        return redirect('kicosca_dashboard')

    edition = KicoscaEdition.get_active()
    if not edition:
        messages.error(request, 'No active KICOSCA edition found. Contact the administrator.')
        return redirect('kicosca_dashboard')

    entry = _get_or_create_entry(reg, edition)
    messages.success(request, f'{reg.county} county registered for {edition.name}.')
    return redirect('kicosca_dashboard')


# ── Add Discipline ─────────────────────────────────────────────────────────────

@kicosca_required
def kicosca_add_discipline(request):
    """County director selects a sport to participate in."""
    reg = _get_reg(request)
    if not reg or not reg.is_approved:
        messages.error(request, 'Your KYISA county registration must be approved first.')
        return redirect('kicosca_dashboard')

    edition = KicoscaEdition.get_active()
    if not edition:
        messages.error(request, 'No active KICOSCA edition.')
        return redirect('kicosca_dashboard')

    entry = _get_or_create_entry(reg, edition)

    if request.method == 'POST':
        sport = request.POST.get('sport', '').strip()
        valid_sports = dict(KicoscaSport.choices)
        if sport not in valid_sports:
            messages.error(request, 'Please select a valid sport.')
        elif KicoscaDiscipline.objects.filter(entry=entry, sport=sport).exists():
            messages.warning(request, f'{valid_sports[sport]} is already added.')
        else:
            KicoscaDiscipline.objects.create(entry=entry, sport=sport)
            messages.success(request, f'{valid_sports[sport]} added.')
        return redirect('kicosca_dashboard')

    # GET — show available sports not yet added
    existing = set(entry.disciplines.values_list('sport', flat=True))
    available = [(k, v) for k, v in KicoscaSport.choices if k not in existing]

    return render(request, 'kicosca/add_discipline.html', {
        'reg':       reg,
        'edition':   edition,
        'available': available,
    })


# ── Discipline Players ─────────────────────────────────────────────────────────

@kicosca_required
def kicosca_discipline_players(request, discipline_pk):
    """List KICOSCA players in a discipline."""
    reg = _get_reg(request)
    discipline = get_object_or_404(
        KicoscaDiscipline,
        pk=discipline_pk,
        entry__county_registration=reg,
    )
    players = discipline.players.all()

    return render(request, 'kicosca/discipline_players.html', {
        'reg':        reg,
        'discipline': discipline,
        'players':    players,
    })


# ── Add Player ─────────────────────────────────────────────────────────────────

@kicosca_required
def kicosca_add_player(request, discipline_pk):
    """County director adds a KICOSCA player with Prembly + KRA verification."""
    reg = _get_reg(request)
    if not reg or not reg.is_approved:
        messages.error(request, 'Your KYISA county registration must be approved first.')
        return redirect('kicosca_dashboard')

    discipline = get_object_or_404(
        KicoscaDiscipline,
        pk=discipline_pk,
        entry__county_registration=reg,
    )

    if not discipline.can_add_player:
        messages.error(request, f'Squad limit reached ({discipline.squad_limit}).')
        return redirect('kicosca_discipline_players', discipline_pk=discipline_pk)

    if request.method == 'POST':
        form = KicoscaPlayerForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save(commit=False)
            player.discipline = discipline
            player.save()
            messages.success(
                request,
                f'{player.full_name} registered for KICOSCA '
                f'({discipline.player_count}/{discipline.squad_limit}).'
            )
            return redirect('kicosca_discipline_players', discipline_pk=discipline_pk)
    else:
        form = KicoscaPlayerForm()

    return render(request, 'kicosca/add_player.html', {
        'form':       form,
        'reg':        reg,
        'discipline': discipline,
    })


# ── Delete Player ──────────────────────────────────────────────────────────────

@kicosca_required
def kicosca_delete_player(request, player_pk):
    """Remove a KICOSCA player."""
    reg = _get_reg(request)
    player = get_object_or_404(
        KicoscaPlayer,
        pk=player_pk,
        discipline__entry__county_registration=reg,
    )
    discipline_pk = player.discipline.pk
    if request.method == 'POST':
        name = player.full_name
        player.delete()
        messages.success(request, f'{name} removed from KICOSCA.')
    return redirect('kicosca_discipline_players', discipline_pk=discipline_pk)


# ── AJAX: KRA PIN Lookup (get PIN from National ID) ───────────────────────────

@login_required(login_url='web_login')
@require_POST
def kicosca_kra_pin_lookup(request):
    """
    AJAX — look up a person's KRA PIN from their National ID via GavaConnect.
    Returns the PIN so the county director can confirm before running the
    full employment check.
    """
    national_id = request.POST.get('national_id', '').strip()
    if not national_id:
        return JsonResponse({'success': False, 'error_message': 'National ID is required.'}, status=400)

    from .kra_service import KRAGavaConnectService
    svc    = KRAGavaConnectService()
    result = svc.get_pin_by_national_id(national_id)
    return JsonResponse(result)


# ── AJAX: KRA Employment Check ────────────────────────────────────────────────

@login_required(login_url='web_login')
@require_POST
def kicosca_kra_verify(request, player_pk):
    """
    AJAX / POST — run KRA employment verification for a KICOSCA player.
    Checks if the player's KRA PIN shows employment by their county government.
    """
    reg = _get_reg(request)
    player = get_object_or_404(
        KicoscaPlayer,
        pk=player_pk,
        discipline__entry__county_registration=reg,
    )

    kra_pin = request.POST.get('kra_pin', player.kra_pin).strip().upper()
    if not kra_pin:
        messages.error(request, 'KRA PIN is required for employment verification.')
        return redirect('kicosca_player_detail', player_pk=player_pk)

    from .kra_service import KRAGavaConnectService
    svc    = KRAGavaConnectService()
    result = svc.verify_county_employment(kra_pin, reg.county)

    # Save KRA PIN if provided
    if kra_pin and not player.kra_pin:
        player.kra_pin = kra_pin

    player.kra_raw_response     = result.raw_response
    player.kra_employer_name    = result.employer_name
    player.kra_employer_pin     = result.employer_pin
    player.kra_verification_ref = result.reference
    player.kra_checked_at       = timezone.now()

    if result.success and result.county_match:
        player.kra_employment_status = EmploymentStatus.VERIFIED
        messages.success(
            request,
            f'✅ KRA confirmed: {player.full_name} is employed by '
            f'{result.employer_name}.'
        )
    elif result.success and result.is_county_employee and not result.county_match:
        player.kra_employment_status = EmploymentStatus.MISMATCH
        messages.warning(
            request,
            f'⚠️ KRA shows employment by "{result.employer_name}" — '
            f'does not match {reg.county} County Government.'
        )
    elif result.success and not result.is_county_employee:
        player.kra_employment_status = EmploymentStatus.FAILED
        messages.error(
            request,
            f'❌ KRA shows employer as "{result.employer_name}" — '
            f'not a county government.'
        )
    else:
        player.kra_employment_status = EmploymentStatus.FAILED
        messages.error(request, f'❌ KRA check failed: {result.error_message}')

    player.save(update_fields=[
        'kra_pin', 'kra_employment_status', 'kra_employer_name',
        'kra_employer_pin', 'kra_verification_ref', 'kra_checked_at',
        'kra_raw_response',
    ])

    return redirect('kicosca_player_detail', player_pk=player_pk)


# ── Player Detail (Verification View) ─────────────────────────────────────────

@login_required(login_url='web_login')
def kicosca_player_detail(request, player_pk):
    """
    View and manage verification steps for a KICOSCA player.
    Accessible to county director (their own county) and admins/VO.
    """
    user = request.user
    player = get_object_or_404(KicoscaPlayer, pk=player_pk)

    # Access control
    can_view = user.is_superuser or user.role in (
        'admin', 'competition_manager', 'verification_officer', 'secretary_general'
    )
    if not can_view and user.role == 'county_sports_admin':
        reg = _get_reg(request)
        if reg and player.discipline.entry.county_registration == reg:
            can_view = True

    if not can_view:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Handle verification actions
    if request.method == 'POST':
        action = request.POST.get('action')

        # Final verification decisions (admin/VO/CM/SG only)
        can_approve = user.is_superuser or user.role in (
            'competition_manager', 'secretary_general', 'verification_officer', 'admin'
        )

        if action == 'verify' and can_approve:
            if player.kra_employment_status != EmploymentStatus.VERIFIED:
                messages.error(request, 'KRA employment must be verified before final approval.')
            else:
                player.verification_status = 'verified'
                player.verified_by         = user
                player.verified_at         = timezone.now()
                player.rejection_reason    = ''
                player.save(update_fields=[
                    'verification_status', 'verified_by', 'verified_at', 'rejection_reason'
                ])
                messages.success(request, f'✅ {player.full_name} verified for KICOSCA.')

        elif action == 'reject' and can_approve:
            reason = request.POST.get('rejection_reason', '').strip()
            player.verification_status = 'rejected'
            player.rejection_reason    = reason
            player.save(update_fields=['verification_status', 'rejection_reason'])
            messages.warning(request, f'❌ {player.full_name} rejected.')

        elif action == 'resubmit' and can_approve:
            reason = request.POST.get('rejection_reason', '').strip()
            player.verification_status = 'resubmit'
            player.rejection_reason    = reason
            player.save(update_fields=['verification_status', 'rejection_reason'])
            messages.info(request, f'🔄 {player.full_name} sent back for resubmission.')

        elif action == 'reset' and can_approve:
            player.verification_status = 'pending'
            player.rejection_reason    = ''
            player.save(update_fields=['verification_status', 'rejection_reason'])
            messages.info(request, f'Reset to pending.')

        return redirect('kicosca_player_detail', player_pk=player_pk)

    can_approve = user.is_superuser or user.role in (
        'competition_manager', 'secretary_general', 'verification_officer', 'admin'
    )
    is_own_county = (
        user.role == 'county_sports_admin' and
        _get_reg(request) and
        player.discipline.entry.county_registration == _get_reg(request)
    )

    return render(request, 'kicosca/player_detail.html', {
        'player':       player,
        'can_approve':  can_approve,
        'is_own_county': is_own_county,
    })


# ── Admin Verification Dashboard ──────────────────────────────────────────────

@login_required(login_url='web_login')
def kicosca_verification_dashboard(request):
    """Admin/VO/KICOSCA officer view of all KICOSCA players across counties."""
    user = request.user
    can_manage = user.is_superuser or user.role in (
        'admin', 'competition_manager', 'verification_officer', 'secretary_general'
    )
    can_view = can_manage or user.role == 'kicosca_officer'

    if not can_view:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    # Handle edition creation
    if request.method == 'POST' and request.POST.get('action') == 'create_edition':
        if can_manage:
            name = request.POST.get('name', '').strip()
            year = request.POST.get('year', '2026')
            host = request.POST.get('host_county', '').strip()
            if name and year:
                KicoscaEdition.objects.update(is_active=False)
                KicoscaEdition.objects.create(
                    name=name, year=int(year), host_county=host, is_active=True
                )
                messages.success(request, f'Edition "{name}" created and set as active.')
            return redirect('kicosca_verification')

    edition = KicoscaEdition.get_active()

    # For KICOSCA officers, only show their county
    if user.role == 'kicosca_officer' and user.county:
        base_qs = KicoscaPlayer.objects.select_related(
            'discipline__entry__county_registration'
        ).filter(
            discipline__entry__edition=edition,
            discipline__entry__county_registration__county=user.county,
        ) if edition else KicoscaPlayer.objects.none()
    else:
        base_qs = KicoscaPlayer.objects.select_related(
            'discipline__entry__county_registration'
        ).filter(
            discipline__entry__edition=edition
        ) if edition else KicoscaPlayer.objects.none()

    base_qs = base_qs.order_by(
        'discipline__entry__county_registration__county', 'last_name'
    )

    county_filter  = request.GET.get('county', '')
    sport_filter   = request.GET.get('sport', '')
    status_filter  = request.GET.get('status', '')
    search         = request.GET.get('q', '')

    players = base_qs
    if county_filter:
        players = players.filter(
            discipline__entry__county_registration__county=county_filter
        )
    if sport_filter:
        players = players.filter(discipline__sport=sport_filter)
    if status_filter:
        players = players.filter(verification_status=status_filter)
    if search:
        from django.db.models import Q
        players = players.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(national_id_number__icontains=search)
        )

    players = list(players)

    # ── Inline API test ────────────────────────────────────────────────────────
    kra_result  = None
    iprs_result = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'test_kra':
            kra_pin = request.POST.get('kra_pin', 'A011124346B').strip().upper()
            county  = request.POST.get('county', 'Nairobi').strip()
            from kicosca.kra_service import KRAGavaConnectService
            svc = KRAGavaConnectService()
            r   = svc.verify_county_employment(kra_pin, county)
            kra_result = {
                'pin': kra_pin, 'county': county,
                'success': r.success, 'county_match': r.county_match,
                'is_county_employee': r.is_county_employee,
                'employer_name': r.employer_name,
                'is_simulation': r.is_simulation,
                'error_message': r.error_message,
            }

        elif action == 'test_iprs':
            nid = request.POST.get('iprs_id', '10101010').strip()
            from teams.prembly_service import PremblyService
            svc = PremblyService()
            r   = svc.lookup_by_national_id(nid)
            iprs_result = {
                'national_id': nid,
                'success': r.success, 'person_found': r.person_found,
                'full_name': r.full_name,
                'date_of_birth': str(r.date_of_birth) if r.date_of_birth else None,
                'serial_number': r.serial_number,
                'has_photo': bool(r.photo),
                'is_simulation': r.is_simulation,
                'error_message': r.error_message,
            }

    return render(request, 'kicosca/verification_dashboard.html', {
        'edition':           edition,
        'players':           players,
        'county_filter':     county_filter,
        'sport_filter':      sport_filter,
        'status_filter':     status_filter,
        'search':            search,
        'sport_choices':     KicoscaSport.choices,
        'can_manage':        can_manage,
        'verified_count':    sum(1 for p in players if p.verification_status == 'verified'),
        'pending_count':     sum(1 for p in players if p.verification_status == 'pending'),
        'rejected_count':    sum(1 for p in players if p.verification_status == 'rejected'),
        'kra_verified_count': sum(1 for p in players if p.kra_employment_status == 'verified'),
        'kra_result':        kra_result,
        'iprs_result':       iprs_result,
    })


# ── API Test Dashboard (admin only) ───────────────────────────────────────────

@login_required(login_url='web_login')
def kicosca_api_test(request):
    """
    Admin-only page to test GavaConnect KRA and Prembly IPRS integrations.
    Run test lookups to confirm credentials are configured and working.
    """
    from django.conf import settings
    user = request.user
    if not (user.is_superuser or user.role in ('admin', 'competition_manager')):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    kra_result   = None
    iprs_result  = None
    kra_pin_result = None

    # GavaConnect config status
    gava_client_id  = getattr(settings, 'GAVACONNECT_CLIENT_ID',  '')
    gava_env        = getattr(settings, 'GAVACONNECT_ENVIRONMENT', 'sandbox')
    gava_configured = bool(gava_client_id)

    # Prembly config status
    prembly_key = getattr(settings, 'PREMBLY_API_KEY', '')
    prembly_env = getattr(settings, 'PREMBLY_ENVIRONMENT', 'sandbox')
    prembly_configured = bool(prembly_key)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'test_kra':
            kra_pin = request.POST.get('kra_pin', 'P051234567A').strip().upper()
            county  = request.POST.get('county', 'Nairobi').strip()
            from .kra_service import KRAGavaConnectService
            svc = KRAGavaConnectService()
            result = svc.verify_county_employment(kra_pin, county)
            kra_result = {
                'pin':             kra_pin,
                'county':          county,
                'success':         result.success,
                'employee_found':  result.employee_found,
                'employer_name':   result.employer_name,
                'employer_pin':    result.employer_pin,
                'is_county_employee': result.is_county_employee,
                'county_match':    result.county_match,
                'is_simulation':   result.is_simulation,
                'error_message':   result.error_message,
            }

        elif action == 'test_kra_pin':
            national_id = request.POST.get('national_id', '12345678').strip()
            from .kra_service import KRAGavaConnectService
            svc = KRAGavaConnectService()
            kra_pin_result = svc.get_pin_by_national_id(national_id)
            kra_pin_result['national_id'] = national_id

        elif action == 'test_iprs':
            national_id = request.POST.get('iprs_id', '10101010').strip()
            from teams.prembly_service import PremblyService
            svc = PremblyService()
            result = svc.lookup_by_national_id(national_id)
            iprs_result = {
                'national_id':    national_id,
                'success':        result.success,
                'person_found':   result.person_found,
                'full_name':      result.full_name,
                'date_of_birth':  str(result.date_of_birth) if result.date_of_birth else None,
                'gender':         result.gender,
                'serial_number':  result.serial_number,
                'date_of_issue':  result.date_of_issue,
                'place_of_birth': result.place_of_birth,
                'has_photo':      bool(result.photo),
                'reference':      result.reference_number,
                'is_simulation':  result.is_simulation,
                'error_message':  result.error_message,
            }

    return render(request, 'kicosca/api_test.html', {
        'gava_configured':   gava_configured,
        'gava_env':          gava_env,
        'prembly_configured': prembly_configured,
        'prembly_env':       prembly_env,
        'kra_result':        kra_result,
        'kra_pin_result':    kra_pin_result,
        'iprs_result':       iprs_result,
    })


# ── Quick Verify from dashboard ───────────────────────────────────────────────

@login_required(login_url='web_login')
@require_POST
def kicosca_quick_verify(request, player_pk):
    """One-click verify a KICOSCA player directly from the verification dashboard."""
    user = request.user
    if not (user.is_superuser or user.role in (
        'admin', 'competition_manager', 'verification_officer', 'secretary_general'
    )):
        messages.error(request, 'Access denied.')
        return redirect('kicosca_verification')

    player = get_object_or_404(KicoscaPlayer, pk=player_pk)

    if player.kra_employment_status != EmploymentStatus.VERIFIED:
        messages.error(request, 'KRA employment must be verified before approval.')
        return redirect('kicosca_verification')

    player.verification_status = 'verified'
    player.verified_by  = user
    player.verified_at  = timezone.now()
    player.rejection_reason = ''
    player.save(update_fields=['verification_status', 'verified_by', 'verified_at', 'rejection_reason'])
    messages.success(request, f'✅ {player.full_name} verified for KICOSCA.')
    return redirect('kicosca_verification')


# ── Create Edition ─────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
@require_POST
def kicosca_create_edition(request):
    """Admin creates a new KICOSCA edition and sets it as active."""
    user = request.user
    if not (user.is_superuser or user.role in ('admin', 'competition_manager', 'secretary_general')):
        messages.error(request, 'Access denied.')
        return redirect('kicosca_verification')

    name = request.POST.get('name', '').strip()
    year = request.POST.get('year', '2026')
    host = request.POST.get('host_county', '').strip()

    if not name:
        messages.error(request, 'Edition name is required.')
        return redirect('kicosca_verification')

    # Deactivate all existing editions
    KicoscaEdition.objects.update(is_active=False)
    edition = KicoscaEdition.objects.create(
        name=name,
        year=int(year),
        host_county=host,
        is_active=True,
    )
    messages.success(request, f'✅ Edition "{edition.name}" created and set as active.')
    return redirect('kicosca_verification')
