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

from teams.models import CountyRegistration
from .models import (
    KicoscaEdition, KicoscaCountyEntry, KicoscaDiscipline,
    KicoscaPlayer, KicoscaSport, KICOSCA_SQUAD_LIMITS, EmploymentStatus,
)
from .forms import KicoscaPlayerForm


# ── Role guard ────────────────────────────────────────────────────────────────
def county_director_required(view):
    @wraps(view)
    @login_required(login_url='web_login')
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'county_sports_admin' and not request.user.is_superuser:
            messages.error(request, 'Only County Sports Directors can access the KICOSCA portal.')
            return redirect('dashboard')
        return view(request, *args, **kwargs)
    return wrapper


def _get_reg(request):
    """Helper — fetch the county registration for the logged-in director."""
    return CountyRegistration.objects.filter(user=request.user).first()


def _get_or_create_entry(reg, edition):
    """Get or create a KicoscaCountyEntry for this county/edition."""
    entry, _ = KicoscaCountyEntry.objects.get_or_create(
        edition=edition,
        county_registration=reg,
    )
    return entry


# ── Dashboard ─────────────────────────────────────────────────────────────────

@county_director_required
def kicosca_dashboard(request):
    """KICOSCA home for the county sports director."""
    reg = _get_reg(request)
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

@county_director_required
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

@county_director_required
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

@county_director_required
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

@county_director_required
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

@county_director_required
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


# ── AJAX: Prembly IPRS Lookup ─────────────────────────────────────────────────

@login_required(login_url='web_login')
@require_POST
def kicosca_iprs_lookup(request):
    """
    AJAX — look up a person by National ID via Prembly IPRS.
    Same as KYISA but namespaced to KICOSCA.
    """
    national_id = request.POST.get('national_id', '').strip()
    if not national_id or not national_id.isdigit() or len(national_id) < 7:
        return JsonResponse({'success': False, 'error_message': 'Invalid National ID.'}, status=400)

    from teams.prembly_service import PremblyService
    svc    = PremblyService()
    result = svc.lookup_by_national_id(national_id)
    return JsonResponse(result.to_dict())


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

    # Handle Prembly IPRS check
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'prembly_check':
            from teams.prembly_service import PremblyService
            svc    = PremblyService()
            result = svc.lookup_by_national_id(player.national_id_number)
            if result.success and result.person_found:
                name_match = any(
                    part in result.full_name.upper()
                    for part in f"{player.first_name} {player.last_name}".upper().split()
                    if len(part) > 2
                )
                dob_match = result.date_of_birth == player.date_of_birth if result.date_of_birth else False
                if name_match and dob_match:
                    player.prembly_status = EmploymentStatus.VERIFIED
                    messages.success(request, f'✅ IPRS verified: {result.full_name}')
                else:
                    player.prembly_status = 'mismatch'
                    messages.warning(
                        request,
                        f'⚠️ IPRS returned {result.full_name} / {result.date_of_birth} — '
                        f'check against registered details.'
                    )
                player.prembly_verified_name = result.full_name
                player.prembly_reference     = result.reference_number
                player.prembly_checked_at    = timezone.now()
                if result.photo:
                    from teams.utils import save_base64_photo
                    try:
                        photo_file = save_base64_photo(
                            result.photo, f"kicosca_{player.national_id_number}"
                        )
                        if photo_file:
                            player.iprs_photo = photo_file
                    except Exception:
                        pass
            else:
                player.prembly_status = EmploymentStatus.FAILED
                player.prembly_checked_at = timezone.now()
                messages.error(request, f'❌ IPRS check failed: {result.error_message}')
            player.save(update_fields=[
                'prembly_status', 'prembly_verified_name', 'prembly_reference',
                'prembly_checked_at', 'iprs_photo',
            ])
            return redirect('kicosca_player_detail', player_pk=player_pk)

        # Final verification decisions (admin/VO/CM/SG only)
        can_approve = user.is_superuser or user.role in (
            'competition_manager', 'secretary_general', 'verification_officer', 'admin'
        )

        if action == 'verify' and can_approve:
            if player.prembly_status != EmploymentStatus.VERIFIED:
                messages.error(request, 'IPRS identity must be verified first.')
            elif player.kra_employment_status != EmploymentStatus.VERIFIED:
                messages.error(request, 'KRA employment must be verified first.')
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
    """Admin/VO view of all KICOSCA players across counties."""
    user = request.user
    if not (user.is_superuser or user.role in (
        'admin', 'competition_manager', 'verification_officer', 'secretary_general'
    )):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    edition = KicoscaEdition.get_active()
    players = KicoscaPlayer.objects.select_related(
        'discipline__entry__county_registration'
    ).filter(
        discipline__entry__edition=edition
    ).order_by('discipline__entry__county_registration__county', 'last_name') if edition else []

    county_filter  = request.GET.get('county', '')
    sport_filter   = request.GET.get('sport', '')
    status_filter  = request.GET.get('status', '')
    search         = request.GET.get('q', '')

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

    return render(request, 'kicosca/verification_dashboard.html', {
        'edition':       edition,
        'players':       players,
        'county_filter': county_filter,
        'sport_filter':  sport_filter,
        'status_filter': status_filter,
        'search':        search,
        'sport_choices': KicoscaSport.choices,
    })
