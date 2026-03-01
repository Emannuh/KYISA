"""
KYISA CMS — Web Frontend Views (Template-Based Portals)
Includes public website pages, public registration, and authenticated CMS portal views.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Q
from functools import wraps
import secrets, string

from accounts.models import User, UserRole, KenyaCounty
from competitions.models import Competition, Fixture, SportType, EXHIBITION_SPORTS, COUNTY_REGISTRATION_FEE_CAP
from teams.models import Team, Player, VerificationStatus, RejectionReason, PLAYER_MIN_AGE, PLAYER_MAX_AGE
from teams.forms import TeamRegistrationForm, PlayerRegistrationForm
from referees.models import (
    RefereeProfile, RefereeAppointment, RefereeAvailability,
    AppointmentStatus, AvailabilityStatus,
)
from referees.forms import RefereeRegistrationForm
from matches.models import MatchReport, MatchEvent, MatchReportStatus, SquadSubmission, SquadPlayer, SquadStatus
from datetime import date, timedelta


# ── ROLE DECORATOR ────────────────────────────────────────────────────────────
def role_required(*roles):
    """Allow access only to users with the given role(s)."""
    def decorator(view):
        @wraps(view)
        @login_required(login_url='web_login')
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
#   PUBLIC WEBSITE VIEWS (No login required)
# ══════════════════════════════════════════════════════════════════════════════

def home_view(request):
    """Public homepage with hero, upcoming fixtures, recent results, stats."""
    now = timezone.now()
    stats = {
        'competitions': Competition.objects.count(),
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
    }
    upcoming_fixtures = Fixture.objects.filter(
        match_date__gte=now
    ).select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('match_date')[:6]

    recent_results = Fixture.objects.filter(
        status='completed'
    ).select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('-match_date')[:6]

    return render(request, 'public/home.html', {
        'active_page': 'home',
        'stats': stats,
        'upcoming_fixtures': upcoming_fixtures,
        'recent_results': recent_results,
    })


def about_view(request):
    """Public about page with mission, values, and county list."""
    stats = {
        'competitions': Competition.objects.count(),
        'teams': Team.objects.count(),
        'players': Player.objects.count(),
    }
    return render(request, 'public/about.html', {
        'active_page': 'about',
        'stats': stats,
        'counties': KenyaCounty.choices,
    })


def public_competitions_view(request):
    """Public competitions listing — grouped by sport, with exhibition marker."""
    all_comps = Competition.objects.all()
    active    = all_comps.filter(status='active')
    upcoming  = all_comps.filter(status__in=['upcoming', 'registration'])
    completed = all_comps.filter(status='completed')

    # KYISA sports catalogue — order matters for display
    SPORT_CATALOGUE = [
        {'key': SportType.SOCCER,           'label': 'Soccer',               'icon': '⚽', 'exhibition': False},
        {'key': SportType.VOLLEYBALL_MEN,   'label': 'Volleyball (Men)',      'icon': '🏐', 'exhibition': False},
        {'key': SportType.VOLLEYBALL_WOMEN, 'label': 'Volleyball (Women)',    'icon': '🏐', 'exhibition': False},
        {'key': SportType.BASKETBALL,       'label': 'Basketball',            'icon': '🏀', 'exhibition': False},
        {'key': SportType.BASKETBALL_3X3,   'label': 'Basketball 3×3',        'icon': '🏀', 'exhibition': False},
        {'key': SportType.HANDBALL,         'label': 'Handball',              'icon': '🤾', 'exhibition': False},
        {'key': SportType.BEACH_VOLLEYBALL, 'label': 'Beach Volleyball',      'icon': '🏖️', 'exhibition': True},
        {'key': SportType.BEACH_HANDBALL,   'label': 'Beach Handball',        'icon': '🏖️', 'exhibition': True},
    ]

    return render(request, 'public/competitions.html', {
        'active_page': 'competitions',
        'active_competitions': active,
        'upcoming_competitions': upcoming,
        'completed_competitions': completed,
        'sport_catalogue': SPORT_CATALOGUE,
        'all_competitions': all_comps,
    })


def public_competition_detail_view(request, pk):
    """Public competition detail with teams and fixtures."""
    competition = get_object_or_404(Competition, pk=pk)
    teams = Team.objects.filter(competition=competition)
    fixtures = Fixture.objects.filter(competition=competition).select_related(
        'home_team', 'away_team', 'venue'
    ).order_by('match_date')
    return render(request, 'public/competition_detail.html', {
        'active_page': 'competitions',
        'competition': competition,
        'teams': teams,
        'fixtures': fixtures,
    })


def public_results_view(request):
    """Public results page — completed matches and upcoming fixtures."""
    now = timezone.now()
    completed = Fixture.objects.filter(
        status='completed'
    ).select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('-match_date')[:30]

    upcoming = Fixture.objects.filter(
        match_date__gte=now
    ).exclude(
        status='completed'
    ).select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('match_date')[:15]

    return render(request, 'public/results.html', {
        'active_page': 'results',
        'completed_fixtures': completed,
        'upcoming_fixtures': upcoming,
    })


def contact_view(request):
    """Public contact page with form."""
    contact_sent = False
    if request.method == 'POST':
        # In production: send email, save to DB, etc.
        contact_sent = True
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
    return render(request, 'public/contact.html', {
        'active_page': 'contact',
        'contact_sent': contact_sent,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   CMS PORTAL VIEWS (Login required)
# ══════════════════════════════════════════════════════════════════════════════

# ── AUTH VIEWS ────────────────────────────────────────────────────────────────

def web_login_view(request):
    """Login page — redirects to dashboard if already authenticated."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if getattr(user, 'is_suspended', False):
                return render(request, 'accounts/login.html', {
                    'error': 'Your account has been suspended. Please contact the administrator.',
                    'email': email,
                })
            login(request, user)
            if getattr(user, 'must_change_password', False):
                messages.warning(request, 'You must change your password before continuing.')
                return redirect('force_change_password')
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard')
        else:
            return render(request, 'accounts/login.html', {
                'error': 'Invalid email or password. Please try again.',
                'email': email,
            })

    return render(request, 'accounts/login.html')


@login_required(login_url='web_login')
def force_change_password_view(request):
    """Force users with one-time passwords to set a new password."""
    if not getattr(request.user, 'must_change_password', False):
        return redirect('dashboard')

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            request.user.set_password(new_password)
            request.user.must_change_password = False
            request.user.save(update_fields=['password', 'must_change_password'])
            login(request, request.user)
            messages.success(request, 'Password changed successfully! Welcome to KYISA CMS.')
            return redirect('dashboard')

    return render(request, 'accounts/force_change_password.html')


def web_logout_view(request):
    """Logout and redirect to home page."""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def dashboard_view(request):
    """Role-based dashboard with stats and recent fixtures."""
    user = request.user

    stats = {
        'competitions': Competition.objects.count(),
        'teams': Team.objects.count(),
        'referees': RefereeProfile.objects.filter(is_approved=True).count(),
        'fixtures': Fixture.objects.count(),
        'players': Player.objects.count(),
    }

    # For team managers, show only their team's data
    if user.role == 'treasurer':
        return redirect('treasurer_dashboard')

    if user.role == 'referee':
        return redirect('referee_portal')

    if user.role == 'team_manager':
        stats['teams'] = Team.objects.filter(manager=user).count()
        my_teams = Team.objects.filter(manager=user)
        recent_fixtures = Fixture.objects.filter(
            Q(home_team__in=my_teams) | Q(away_team__in=my_teams)
        ).order_by('-match_date')[:10]
    else:
        recent_fixtures = Fixture.objects.select_related(
            'competition', 'home_team', 'away_team'
        ).order_by('-match_date')[:10]

    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'recent_fixtures': recent_fixtures,
    })


# ── COMPETITIONS ──────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def competitions_list_view(request):
    """List all competitions."""
    competitions = Competition.objects.all()
    return render(request, 'competitions/list.html', {
        'competitions': competitions,
    })


@login_required(login_url='web_login')
def competition_detail_view(request, pk):
    """Competition detail with teams and fixtures."""
    competition = get_object_or_404(Competition, pk=pk)
    teams = Team.objects.filter(competition=competition)
    fixtures = Fixture.objects.filter(competition=competition).select_related(
        'home_team', 'away_team', 'venue'
    )
    return render(request, 'competitions/detail.html', {
        'competition': competition,
        'teams': teams,
        'fixtures': fixtures,
    })


# ── TEAMS ─────────────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def teams_list_view(request):
    """List teams — team managers see only their teams."""
    user = request.user
    if user.role == 'team_manager':
        teams = Team.objects.filter(manager=user)
    else:
        teams = Team.objects.all()
    return render(request, 'teams/list.html', {'teams': teams})


@login_required(login_url='web_login')
def team_detail_view(request, pk):
    """Team detail with players and player management."""
    team = get_object_or_404(Team, pk=pk)
    players = Player.objects.filter(team=team).order_by('shirt_number')

    # Check if user can manage this team
    can_manage = (
        request.user.is_superuser or
        request.user.role in ('admin', 'competition_manager') or
        team.manager == request.user
    )

    return render(request, 'teams/detail.html', {
        'team': team,
        'players': players,
        'can_manage': can_manage,
    })


# ── PLAYER MANAGEMENT ────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def add_player_view(request, team_pk):
    """Add a player to a team (team manager or admin)."""
    team = get_object_or_404(Team, pk=team_pk)

    # Only team manager or admins can add players
    is_manager = team.manager == request.user
    is_admin = request.user.is_superuser or request.user.role in ('admin', 'competition_manager')
    if not is_manager and not is_admin:
        messages.error(request, 'You do not have permission to manage this team.')
        return redirect('teams_list')

    # Suspended teams cannot add players
    if team.status == 'suspended':
        messages.warning(request, 'This team is suspended. Players cannot be added.')
        return redirect('team_detail', pk=team.pk)

    from teams.forms import PlayerRegistrationForm

    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save(commit=False)
            player.team = team

            # Check jersey number uniqueness within team
            if Player.objects.filter(team=team, shirt_number=player.shirt_number).exists():
                messages.error(request, f'Shirt number {player.shirt_number} is already taken in this team.')
            elif player.national_id_number and Player.objects.filter(national_id_number=player.national_id_number).exists():
                messages.error(request, f'A player with National ID {player.national_id_number} is already registered.')
            else:
                player.save()
                if not player.is_age_eligible:
                    messages.warning(request, (
                        f'{player.get_full_name()} added but AUTO-REJECTED — '
                        f'age {player.age} is outside the {PLAYER_MIN_AGE}-{PLAYER_MAX_AGE} bracket.'
                    ))
                elif not player.documents_uploaded:
                    messages.info(request, (
                        f'{player.get_full_name()} added to {team.name}. '
                        f'Documents pending — upload ID, birth certificate & photo for verification.'
                    ))
                else:
                    messages.success(request, (
                        f'{player.get_full_name()} added to {team.name}. '
                        f'Documents submitted — pending admin verification.'
                    ))

                action = request.POST.get('action', 'add_more')
                if action == 'finish':
                    return redirect('team_detail', pk=team.pk)
                # Reset form for another player
                form = PlayerRegistrationForm()
    else:
        form = PlayerRegistrationForm()

    existing_players = Player.objects.filter(team=team).order_by('shirt_number')

    return render(request, 'portal/add_player.html', {
        'form': form,
        'team': team,
        'players': existing_players,
        'player_count': existing_players.count(),
    })


@login_required(login_url='web_login')
def edit_player_view(request, player_pk):
    """Edit a player's details."""
    player = get_object_or_404(Player, pk=player_pk)
    team = player.team

    is_manager = team.manager == request.user
    is_admin = request.user.is_superuser or request.user.role in ('admin', 'competition_manager')
    if not is_manager and not is_admin:
        messages.error(request, 'You do not have permission to edit this player.')
        return redirect('teams_list')

    from teams.forms import PlayerRegistrationForm

    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, request.FILES, instance=player)
        if form.is_valid():
            # Check jersey number uniqueness (exclude current player)
            new_shirt = form.cleaned_data['shirt_number']
            if Player.objects.filter(team=team, shirt_number=new_shirt).exclude(pk=player.pk).exists():
                messages.error(request, f'Shirt number {new_shirt} is already taken.')
            else:
                form.save()
                messages.success(request, f'{player.get_full_name()} updated.')
                return redirect('team_detail', pk=team.pk)
    else:
        form = PlayerRegistrationForm(instance=player)

    return render(request, 'portal/edit_player.html', {
        'form': form,
        'player': player,
        'team': team,
    })


@login_required(login_url='web_login')
def delete_player_view(request, player_pk):
    """Delete a player from a team."""
    player = get_object_or_404(Player, pk=player_pk)
    team = player.team

    is_manager = team.manager == request.user
    is_admin = request.user.is_superuser or request.user.role in ('admin', 'competition_manager')
    if not is_manager and not is_admin:
        messages.error(request, 'Permission denied.')
        return redirect('teams_list')

    if request.method == 'POST':
        name = player.get_full_name()
        player.delete()
        messages.success(request, f'{name} removed from {team.name}.')
        return redirect('team_detail', pk=team.pk)

    return render(request, 'portal/delete_player.html', {
        'player': player,
        'team': team,
    })


# ── REFEREES ──────────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def referees_list_view(request):
    """List referees and appointments."""
    user = request.user
    if user.role == 'referee':
        try:
            referees = [user.referee_profile]
            appointments = RefereeAppointment.objects.filter(
                referee=user.referee_profile
            ).select_related('fixture__home_team', 'fixture__away_team')
        except RefereeProfile.DoesNotExist:
            referees = []
            appointments = []
    else:
        referees = RefereeProfile.objects.select_related('user').all()
        appointments = RefereeAppointment.objects.select_related(
            'fixture__home_team', 'fixture__away_team', 'referee__user'
        ).order_by('-appointed_at')[:20]

    return render(request, 'referees/list.html', {
        'referees': referees,
        'appointments': appointments,
    })


# ── MATCHES ───────────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def matches_list_view(request):
    """List fixtures and match reports — with role-appropriate actions."""
    user = request.user

    if user.role == 'team_manager':
        my_teams = Team.objects.filter(manager=user)
        fixtures = Fixture.objects.filter(
            Q(home_team__in=my_teams) | Q(away_team__in=my_teams)
        ).select_related('competition', 'home_team', 'away_team', 'venue').order_by('-match_date')
    elif user.role == 'referee':
        try:
            fixtures = Fixture.objects.filter(
                referee_appointments__referee=user.referee_profile
            ).select_related('competition', 'home_team', 'away_team', 'venue').order_by('-match_date')
        except RefereeProfile.DoesNotExist:
            fixtures = Fixture.objects.none()
    else:
        fixtures = Fixture.objects.select_related(
            'competition', 'home_team', 'away_team', 'venue'
        ).order_by('-match_date')

    # Annotate fixtures with squad / report info for template buttons
    now = timezone.now()
    fixture_data = []
    for f in fixtures:
        fd = {'fixture': f}
        # Squad submission status for this user's team
        if user.role == 'team_manager':
            my_team = f.home_team if f.home_team in my_teams else (f.away_team if f.away_team in my_teams else None)
            if my_team:
                squad = SquadSubmission.objects.filter(fixture=f, team=my_team).first()
                fd['squad'] = squad
                fd['my_team'] = my_team
                try:
                    fd['deadline_passed'] = now > f.squad_deadline
                except Exception:
                    fd['deadline_passed'] = True
        # Match report
        try:
            fd['report'] = f.match_report
        except MatchReport.DoesNotExist:
            fd['report'] = None
        fixture_data.append(fd)

    match_reports = MatchReport.objects.select_related(
        'fixture__home_team', 'fixture__away_team', 'referee__user'
    ).order_by('-submitted_at')[:30]

    # For referee_manager: pending reports
    pending_reports = MatchReport.objects.filter(
        status=MatchReportStatus.SUBMITTED
    ).select_related('fixture__home_team', 'fixture__away_team', 'referee__user') if user.role in ('referee_manager', 'admin') else []

    return render(request, 'matches/list.html', {
        'fixture_data': fixture_data,
        'fixtures': fixtures,  # Keep backward compat
        'match_reports': match_reports,
        'pending_reports': pending_reports,
    })


# ── PROFILE ───────────────────────────────────────────────────────────────────

@login_required(login_url='web_login')
def profile_view(request):
    """User profile page."""
    return render(request, 'accounts/profile.html')


@login_required(login_url='web_login')
def change_password_view(request):
    """Handle password change."""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            request.user.set_password(new_password)
            request.user.must_change_password = False
            request.user.save(update_fields=['password', 'must_change_password'])
            login(request, request.user)
            messages.success(request, 'Password updated successfully!')

    return redirect('web_profile')


# ══════════════════════════════════════════════════════════════════════════════
#   PUBLIC REGISTRATION VIEWS (No login required)
# ══════════════════════════════════════════════════════════════════════════════

def team_register_view(request):
    """Public team registration — creates team with 'pending' status."""
    if request.method == 'POST':
        form = TeamRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            team = form.save(commit=False)
            team.status = 'pending'
            team.save()
            messages.success(request, mark_safe(
                f'<strong>Team Registration Successful!</strong><br>'
                f'Team: <strong>{team.name}</strong><br>'
                f'County: {team.county}<br><br>'
                f'Your registration is now <strong>pending approval</strong>.<br>'
                f'You will be notified once an administrator reviews your application.'
            ))
            return redirect('team_register_success')
    else:
        form = TeamRegistrationForm()
    return render(request, 'public/team_register.html', {
        'form': form,
        'active_page': 'register',
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


def team_register_success_view(request):
    """Success page after team registration."""
    return render(request, 'public/team_register_success.html', {
        'active_page': 'register',
    })


def referee_register_view(request):
    """Public referee registration — creates User + RefereeProfile (pending)."""
    if request.method == 'POST':
        form = RefereeRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            # Create user account (inactive until approved)
            random_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            user = User.objects.create_user(
                email=cd['email'],
                password=random_pw,
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                phone=cd.get('phone', ''),
                county=cd.get('county', ''),
                role=UserRole.REFEREE,
                is_active=False,
            )
            # Create referee profile
            profile = RefereeProfile.objects.create(
                user=user,
                license_number=cd['license_number'],
                level=cd.get('level') or 'County',
                county=cd.get('county', ''),
                id_number=cd.get('id_number', ''),
                years_experience=cd.get('years_experience') or 0,
                is_approved=False,
            )
            # Save profile picture if uploaded
            if cd.get('profile_picture'):
                profile.profile_picture = cd['profile_picture']
                profile.save(update_fields=['profile_picture'])
            messages.success(request, mark_safe(
                f'<strong>Registration Successful!</strong><br>'
                f'Thank you, <strong>{cd["first_name"]} {cd["last_name"]}</strong>!<br>'
                f'License: <code>{cd["license_number"]}</code><br><br>'
                f'<strong>Next Steps:</strong><br>'
                f'1. Wait for admin approval<br>'
                f'2. You will receive login credentials via email<br>'
                f'3. Log in and change your password'
            ))
            return redirect('referee_register_success')
    else:
        form = RefereeRegistrationForm()
    return render(request, 'public/referee_register.html', {
        'form': form,
        'active_page': 'register',
    })


def referee_register_success_view(request):
    """Success page after referee registration."""
    return render(request, 'public/referee_register_success.html', {
        'active_page': 'register',
    })


# ══════════════════════════════════════════════════════════════════════════════
#   ADMIN / MANAGER — TEAM APPROVAL VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('admin', 'competition_manager')
def pending_teams_view(request):
    """List teams awaiting approval."""
    pending = Team.objects.filter(status='pending').order_by('-registered_at')

    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action = request.POST.get('action')
        team = get_object_or_404(Team, pk=team_id)

        if action == 'approve':
            team.status = 'registered'
            team.save()

            # Create manager account if a contact email was provided
            if team.contact_email and not team.manager:
                try:
                    default_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                    manager = User.objects.create_user(
                        email=team.contact_email,
                        password=default_pw,
                        first_name=team.name,
                        last_name='Manager',
                        role=UserRole.TEAM_MANAGER,
                        county=team.county,
                    )
                    team.manager = manager
                    team.save()
                    messages.success(request, mark_safe(
                        f'✅ <strong>{team.name}</strong> approved!<br>'
                        f'Manager account: <code>{team.contact_email}</code><br>'
                        f'Temp password: <code>{default_pw}</code>'
                    ))
                except Exception as e:
                    messages.warning(request, f'Team approved but manager account failed: {e}')
            else:
                messages.success(request, f'✅ {team.name} has been approved.')

        elif action == 'reject':
            team.status = 'suspended'
            team.save()
            messages.warning(request, f'❌ {team.name} registration rejected.')

        return redirect('pending_teams')

    return render(request, 'portal/pending_teams.html', {
        'pending_teams': pending,
        'stats': {
            'pending': pending.count(),
            'registered': Team.objects.filter(status='registered').count(),
            'total': Team.objects.count(),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
#   ADMIN / MANAGER — REFEREE APPROVAL VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('admin', 'referee_manager')
def pending_referees_view(request):
    """List referees awaiting approval."""
    pending = RefereeProfile.objects.filter(
        is_approved=False
    ).select_related('user').order_by('-created_at')

    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')
        profile = get_object_or_404(RefereeProfile, pk=profile_id)

        if action == 'approve':
            profile.is_approved = True
            profile.approved_by = request.user
            profile.approved_at = timezone.now()
            profile.save()

            # Activate the user account
            user = profile.user
            user.is_active = True
            temp_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            user.set_password(temp_pw)
            user.save()

            messages.success(request, mark_safe(
                f'✅ <strong>{user.get_full_name()}</strong> approved!<br>'
                f'Login: <code>{user.email}</code><br>'
                f'Temp password: <code>{temp_pw}</code><br>'
                f'Ask them to change their password on first login.'
            ))

        elif action == 'reject':
            user = profile.user
            user_name = user.get_full_name()
            profile.delete()
            user.delete()
            messages.warning(request, f'❌ {user_name} registration rejected and removed.')

        return redirect('pending_referees')

    return render(request, 'portal/pending_referees.html', {
        'pending_referees': pending,
        'stats': {
            'pending': pending.count(),
            'approved': RefereeProfile.objects.filter(is_approved=True).count(),
            'total': RefereeProfile.objects.count(),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
#   ADMIN — PLAYER VERIFICATION VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('admin', 'competition_manager')
def player_verification_list_view(request):
    """
    Admin view showing players grouped by verification status.
    Tabs: Pending | Verified | Rejected
    """
    tab = request.GET.get('tab', 'pending')

    pending_players = Player.objects.filter(
        verification_status=VerificationStatus.PENDING,
        team__status='registered',
    ).select_related('team').order_by('team__name', 'shirt_number')

    verified_players = Player.objects.filter(
        verification_status=VerificationStatus.VERIFIED,
    ).select_related('team', 'verified_by').order_by('team__name', 'shirt_number')

    rejected_players = Player.objects.filter(
        verification_status=VerificationStatus.REJECTED,
    ).select_related('team').order_by('team__name', 'shirt_number')

    return render(request, 'portal/player_verification_list.html', {
        'tab': tab,
        'pending_players': pending_players,
        'verified_players': verified_players,
        'rejected_players': rejected_players,
        'stats': {
            'pending': pending_players.count(),
            'verified': verified_players.count(),
            'rejected': rejected_players.count(),
        },
        'rejection_reasons': RejectionReason.choices,
    })


@role_required('admin', 'competition_manager')
def verify_player_view(request, player_pk):
    """Admin view to inspect a single player's documents and verify/reject."""
    player = get_object_or_404(Player, pk=player_pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'verify':
            player.verification_status = VerificationStatus.VERIFIED
            player.rejection_reason = ''
            player.rejection_notes = ''
            player.verified_by = request.user
            player.verified_at = timezone.now()
            player.status = 'eligible'
            player.save()
            messages.success(request, f'✅ {player.get_full_name()} has been verified.')

        elif action == 'reject':
            reason = request.POST.get('rejection_reason', RejectionReason.OTHER)
            notes = request.POST.get('rejection_notes', '')
            player.verification_status = VerificationStatus.REJECTED
            player.rejection_reason = reason
            player.rejection_notes = notes
            player.status = 'ineligible'
            player.verified_by = request.user
            player.verified_at = timezone.now()
            player.save()
            messages.warning(request, f'❌ {player.get_full_name()} has been rejected: {player.get_rejection_reason_display()}')

        elif action == 'reset':
            # Allow re-submission — set back to pending
            player.verification_status = VerificationStatus.PENDING
            player.rejection_reason = ''
            player.rejection_notes = ''
            player.verified_by = None
            player.verified_at = None
            player.status = 'eligible'
            player.save()
            messages.info(request, f'🔄 {player.get_full_name()} reset to pending verification.')

        return redirect('player_verification_list')

    return render(request, 'portal/verify_player.html', {
        'player': player,
        'rejection_reasons': RejectionReason.choices,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   SQUAD SELECTION (Team Manager)
# ══════════════════════════════════════════════════════════════════════════════

@role_required('team_manager')
def squad_select_view(request, fixture_pk):
    """Team Manager picks starters & subs for a fixture (≥2 hrs before KO)."""
    from django.conf import settings as conf

    fixture = get_object_or_404(Fixture, pk=fixture_pk)
    user = request.user

    # Determine the manager's team in this fixture
    my_teams = Team.objects.filter(manager=user)
    if fixture.home_team in my_teams:
        team = fixture.home_team
    elif fixture.away_team in my_teams:
        team = fixture.away_team
    else:
        messages.error(request, 'Your team is not involved in this fixture.')
        return redirect('matches_list')

    # Only treasurer-approved teams can submit squads / play
    if not team.payment_confirmed:
        messages.error(request, 'Your team cannot participate — payment has not been confirmed by the treasurer.')
        return redirect('matches_list')

    deadline = fixture.squad_deadline
    now = timezone.now()
    deadline_passed = now > deadline

    # Existing submission
    existing = SquadSubmission.objects.filter(fixture=fixture, team=team).first()

    # Only verified & eligible players
    players = Player.objects.filter(
        team=team, status='eligible', verification_status='verified'
    ).order_by('shirt_number')

    starter_ids = []
    sub_ids = []
    if existing:
        starter_ids = list(existing.squad_players.filter(is_starter=True).values_list('player_id', flat=True))
        sub_ids = list(existing.squad_players.filter(is_starter=False).values_list('player_id', flat=True))

    if request.method == 'POST':
        if deadline_passed:
            messages.error(request, f'Squad submission deadline has passed ({deadline.strftime("%d %b %Y %H:%M")}).')
            return redirect('matches_list')

        selected_starters = request.POST.getlist('starters')
        selected_subs = request.POST.getlist('subs')

        starters_int = [int(x) for x in selected_starters if x]
        subs_int = [int(x) for x in selected_subs if x]

        # Validate no overlap
        overlap = set(starters_int) & set(subs_int)
        if overlap:
            messages.error(request, 'A player cannot be both a starter and a substitute.')
        elif len(starters_int) != conf.SQUAD_MAX_STARTERS:
            messages.error(request, f'Exactly {conf.SQUAD_MAX_STARTERS} starters required. You selected {len(starters_int)}.')
        elif len(subs_int) > conf.SQUAD_MAX_SUBS:
            messages.error(request, f'Maximum {conf.SQUAD_MAX_SUBS} substitutes allowed.')
        elif len(starters_int) + len(subs_int) < conf.SQUAD_MIN_PLAYERS:
            messages.error(request, f'Minimum {conf.SQUAD_MIN_PLAYERS} players required.')
        else:
            # Create or update
            if existing:
                existing.squad_players.all().delete()
                submission = existing
            else:
                submission = SquadSubmission.objects.create(fixture=fixture, team=team)

            submission.status = SquadStatus.SUBMITTED
            submission.submitted_at = timezone.now()
            submission.rejection_reason = ''
            submission.save()

            for pid in starters_int:
                p = Player.objects.get(pk=pid, team=team)
                SquadPlayer.objects.create(submission=submission, player=p, is_starter=True, shirt_number=p.shirt_number)
            for pid in subs_int:
                p = Player.objects.get(pk=pid, team=team)
                SquadPlayer.objects.create(submission=submission, player=p, is_starter=False, shirt_number=p.shirt_number)

            messages.success(request, f'✅ Squad submitted for {fixture.home_team} vs {fixture.away_team}.')
            return redirect('matches_list')

    return render(request, 'portal/squad_select.html', {
        'fixture': fixture,
        'team': team,
        'players': players,
        'existing': existing,
        'deadline': deadline,
        'deadline_passed': deadline_passed,
        'starter_ids': starter_ids,
        'sub_ids': sub_ids,
        'settings': {
            'min_players': conf.SQUAD_MIN_PLAYERS,
            'max_players': conf.SQUAD_MAX_PLAYERS,
            'max_starters': conf.SQUAD_MAX_STARTERS,
            'max_subs': conf.SQUAD_MAX_SUBS,
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
#   SQUAD APPROVAL (Referee / CR)
# ══════════════════════════════════════════════════════════════════════════════

@role_required('referee', 'admin', 'competition_manager')
def squad_review_list_view(request):
    """List squads awaiting referee approval."""
    user = request.user
    if user.role == 'referee':
        try:
            profile = user.referee_profile
            # Show squads for fixtures the referee is appointed to
            appointed_fixture_ids = RefereeAppointment.objects.filter(
                referee=profile, role='centre'
            ).values_list('fixture_id', flat=True)
            pending_squads = SquadSubmission.objects.filter(
                fixture_id__in=appointed_fixture_ids,
                status=SquadStatus.SUBMITTED,
            ).select_related('fixture__home_team', 'fixture__away_team', 'team')
        except RefereeProfile.DoesNotExist:
            pending_squads = SquadSubmission.objects.none()
    else:
        pending_squads = SquadSubmission.objects.filter(
            status=SquadStatus.SUBMITTED,
        ).select_related('fixture__home_team', 'fixture__away_team', 'team')

    all_squads = SquadSubmission.objects.exclude(
        status=SquadStatus.DRAFT
    ).select_related('fixture__home_team', 'fixture__away_team', 'team').order_by('-submitted_at')[:30]

    return render(request, 'portal/squad_review_list.html', {
        'pending_squads': pending_squads,
        'all_squads': all_squads,
    })


@role_required('referee', 'admin', 'competition_manager')
def squad_review_view(request, squad_pk):
    """Referee reviews a submitted squad — approve or reject."""
    squad = get_object_or_404(SquadSubmission, pk=squad_pk)
    squad_players = squad.squad_players.select_related('player').order_by('-is_starter', 'shirt_number')
    starters = [sp for sp in squad_players if sp.is_starter]
    subs = [sp for sp in squad_players if not sp.is_starter]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            squad.status = SquadStatus.APPROVED
            squad.reviewed_by = request.user
            squad.reviewed_at = timezone.now()
            squad.save()
            messages.success(request, f'✅ Squad approved: {squad.team.name} for {squad.fixture}')
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            squad.status = SquadStatus.REJECTED
            squad.reviewed_by = request.user
            squad.reviewed_at = timezone.now()
            squad.rejection_reason = reason
            squad.save()
            messages.warning(request, f'❌ Squad rejected: {squad.team.name}')
        return redirect('squad_review_list')

    return render(request, 'portal/squad_review.html', {
        'squad': squad,
        'starters': starters,
        'subs': subs,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   MATCH REPORT (Referee submits)
# ══════════════════════════════════════════════════════════════════════════════

@role_required('referee', 'admin')
def match_report_form_view(request, fixture_pk):
    """Referee creates / edits a match report for a fixture they officiated."""
    fixture = get_object_or_404(Fixture, pk=fixture_pk)
    user = request.user

    # Get or create report
    try:
        report = MatchReport.objects.get(fixture=fixture)
    except MatchReport.DoesNotExist:
        report = None

    # If report already approved, don't allow edits
    if report and report.status == MatchReportStatus.APPROVED:
        messages.info(request, 'This match report has already been approved.')
        return redirect('match_report_detail', report_pk=report.pk)

    # Get players from both teams for event recording
    home_players = Player.objects.filter(team=fixture.home_team).order_by('shirt_number')
    away_players = Player.objects.filter(team=fixture.away_team).order_by('shirt_number')

    if request.method == 'POST':
        # ── Parse main report fields ──
        home_score = int(request.POST.get('home_score', 0))
        away_score = int(request.POST.get('away_score', 0))
        home_yellow = int(request.POST.get('home_yellow_cards', 0))
        away_yellow = int(request.POST.get('away_yellow_cards', 0))
        home_red = int(request.POST.get('home_red_cards', 0))
        away_red = int(request.POST.get('away_red_cards', 0))
        match_duration = int(request.POST.get('match_duration', 90))
        added_time_ht = int(request.POST.get('added_time_ht', 0))
        added_time_ft = int(request.POST.get('added_time_ft', 0))
        pitch_condition = request.POST.get('pitch_condition', 'good')
        weather = request.POST.get('weather', '')
        attendance = request.POST.get('attendance', '') or None
        referee_notes = request.POST.get('referee_notes', '')
        is_abandoned = request.POST.get('is_abandoned') == 'on'
        abandonment_reason = request.POST.get('abandonment_reason', '')

        if report:
            # Update
            report.home_score = home_score
            report.away_score = away_score
            report.home_yellow_cards = home_yellow
            report.away_yellow_cards = away_yellow
            report.home_red_cards = home_red
            report.away_red_cards = away_red
            report.match_duration = match_duration
            report.added_time_ht = added_time_ht
            report.added_time_ft = added_time_ft
            report.pitch_condition = pitch_condition
            report.weather = weather
            report.attendance = int(attendance) if attendance else None
            report.referee_notes = referee_notes
            report.is_abandoned = is_abandoned
            report.abandonment_reason = abandonment_reason
        else:
            # Determine referee profile
            ref_profile = None
            if hasattr(user, 'referee_profile'):
                ref_profile = user.referee_profile
            report = MatchReport(
                fixture=fixture,
                referee=ref_profile,
                home_score=home_score,
                away_score=away_score,
                home_yellow_cards=home_yellow,
                away_yellow_cards=away_yellow,
                home_red_cards=home_red,
                away_red_cards=away_red,
                match_duration=match_duration,
                added_time_ht=added_time_ht,
                added_time_ft=added_time_ft,
                pitch_condition=pitch_condition,
                weather=weather,
                attendance=int(attendance) if attendance else None,
                referee_notes=referee_notes,
                is_abandoned=is_abandoned,
                abandonment_reason=abandonment_reason,
            )

        action = request.POST.get('submit_action', 'draft')
        if action == 'submit':
            report.status = MatchReportStatus.SUBMITTED
            report.submitted_at = timezone.now()
        else:
            report.status = MatchReportStatus.DRAFT

        report.save()

        # ── Parse events ──
        report.events.all().delete()  # Replace all events
        event_count = int(request.POST.get('event_count', 0))
        for i in range(event_count):
            evt_type = request.POST.get(f'event_{i}_type', '')
            evt_team = request.POST.get(f'event_{i}_team', '')
            evt_player = request.POST.get(f'event_{i}_player', '')
            evt_minute = request.POST.get(f'event_{i}_minute', '')
            evt_notes = request.POST.get(f'event_{i}_notes', '')
            if evt_type and evt_minute:
                MatchEvent.objects.create(
                    report=report,
                    team_id=int(evt_team) if evt_team else fixture.home_team_id,
                    player_id=int(evt_player) if evt_player else None,
                    event_type=evt_type,
                    minute=int(evt_minute),
                    notes=evt_notes,
                )

        if action == 'submit':
            messages.success(request, '✅ Match report submitted for review.')
        else:
            messages.info(request, '📝 Match report saved as draft.')
        return redirect('matches_list')

    # Get existing events
    events = report.events.all().order_by('minute') if report else []

    # ── Auto-populate from approved squads (FKF pattern) ──
    home_squad = SquadSubmission.objects.filter(
        fixture=fixture, team=fixture.home_team, status=SquadStatus.APPROVED
    ).first()
    away_squad = SquadSubmission.objects.filter(
        fixture=fixture, team=fixture.away_team, status=SquadStatus.APPROVED
    ).first()
    home_starters = home_squad.squad_players.filter(is_starter=True).select_related('player').order_by('shirt_number') if home_squad else []
    home_subs = home_squad.squad_players.filter(is_starter=False).select_related('player').order_by('shirt_number') if home_squad else []
    away_starters = away_squad.squad_players.filter(is_starter=True).select_related('player').order_by('shirt_number') if away_squad else []
    away_subs = away_squad.squad_players.filter(is_starter=False).select_related('player').order_by('shirt_number') if away_squad else []

    # Other officials appointed to this match
    match_officials = RefereeAppointment.objects.filter(
        fixture=fixture
    ).select_related('referee__user').order_by('role')

    return render(request, 'portal/match_report_form.html', {
        'fixture': fixture,
        'report': report,
        'events': events,
        'home_players': home_players,
        'away_players': away_players,
        'pitch_choices': [('excellent', 'Excellent'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor')],
        'event_types': MatchEvent.EVENT_TYPES,
        # Squad data
        'home_squad': home_squad,
        'away_squad': away_squad,
        'home_starters': home_starters,
        'home_subs': home_subs,
        'away_starters': away_starters,
        'away_subs': away_subs,
        'match_officials': match_officials,
    })


@login_required(login_url='web_login')
def match_report_detail_view(request, report_pk):
    """View a match report (read-only)."""
    report = get_object_or_404(MatchReport, pk=report_pk)
    events = report.events.select_related('team', 'player').order_by('minute')
    return render(request, 'portal/match_report_detail.html', {
        'report': report,
        'events': events,
    })


@role_required('referee_manager', 'admin')
def match_report_review_view(request, report_pk):
    """Referee Manager approves or returns a match report."""
    report = get_object_or_404(MatchReport, pk=report_pk)
    events = report.events.select_related('team', 'player').order_by('minute')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('reviewer_notes', '')

        if action == 'approve':
            report.status = MatchReportStatus.APPROVED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.reviewer_notes = notes

            # Update fixture with final score
            fixture = report.fixture
            fixture.home_score = report.home_score
            fixture.away_score = report.away_score
            fixture.status = 'completed'
            fixture.save(update_fields=['home_score', 'away_score', 'status'])

            # Update pool standings
            from matches.views import _update_standings
            _update_standings(fixture)

            report.save()
            messages.success(request, f'✅ Match report approved — {fixture.home_team} {report.home_score}-{report.away_score} {fixture.away_team}')

        elif action == 'return':
            report.status = MatchReportStatus.RETURNED
            report.reviewer_notes = notes
            report.save()
            messages.warning(request, f'🔄 Match report returned for revision.')

        return redirect('matches_list')

    return render(request, 'portal/match_report_review.html', {
        'report': report,
        'events': events,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   REFEREE APPOINTMENT CONFIRM / DECLINE
# ══════════════════════════════════════════════════════════════════════════════

@role_required('referee')
def appointment_action_view(request, appointment_pk):
    """Referee confirms or declines a match appointment."""
    user = request.user
    try:
        appointment = RefereeAppointment.objects.select_related(
            'fixture__home_team', 'fixture__away_team', 'fixture__venue', 'fixture__competition'
        ).get(pk=appointment_pk, referee=user.referee_profile)
    except (RefereeAppointment.DoesNotExist, RefereeProfile.DoesNotExist):
        messages.error(request, 'Appointment not found.')
        return redirect('referees_list')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'confirm':
            appointment.status = 'confirmed'
            appointment.confirmed_at = timezone.now()
            appointment.save()
            messages.success(request, f'✅ Appointment confirmed: {appointment.fixture}')
        elif action == 'decline':
            appointment.status = 'declined'
            appointment.notes = request.POST.get('notes', '')
            appointment.save()
            messages.warning(request, f'❌ Appointment declined: {appointment.fixture}')
        return redirect('referees_list')

    return render(request, 'portal/appointment_action.html', {
        'appointment': appointment,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   REFEREE DASHBOARD  (Comprehensive — borrowed from FKF)
# ══════════════════════════════════════════════════════════════════════════════

@role_required('referee')
def referee_dashboard_view(request):
    """
    Full referee portal dashboard showing:
    – pending confirmations, upcoming / current / completed matches
    – pending match reports, squad approvals, availability summary
    """
    user = request.user
    try:
        profile = user.referee_profile
    except RefereeProfile.DoesNotExist:
        # Render an empty-state dashboard instead of redirecting (avoids loop)
        return render(request, 'portal/referee_dashboard.html', {
            'profile': None,
            'no_profile': True,
            'pending_confirmation': [],
            'upcoming_matches': [],
            'current_matches': [],
            'completed_matches': [],
            'pending_reports': [],
            'draft_reports': [],
            'returned_reports': [],
            'pending_squads': [],
            'availability_calendar': [],
            'total_appointments': 0,
        })

    today = date.today()

    appointments = RefereeAppointment.objects.filter(
        referee=profile
    ).select_related(
        'fixture__home_team', 'fixture__away_team',
        'fixture__venue', 'fixture__competition',
    ).order_by('fixture__match_date')

    pending_confirmation = []
    upcoming_matches = []
    completed_matches = []
    current_matches = []

    for appt in appointments:
        match_date = appt.fixture.match_date
        info = {
            'appointment': appt,
            'fixture': appt.fixture,
            'role': appt.get_role_display(),
            'status': appt.status,
            'match_date': match_date,
        }
        if match_date == today:
            current_matches.append(info)
            if appt.status == AppointmentStatus.PENDING:
                pending_confirmation.append(info)
        elif match_date > today:
            if appt.status == AppointmentStatus.PENDING:
                pending_confirmation.append(info)
            upcoming_matches.append(info)
        else:
            completed_matches.append(info)

    # Pending match reports  (fixtures where referee is centre and no report submitted yet)
    centre_fixture_ids = RefereeAppointment.objects.filter(
        referee=profile, role='centre',
    ).values_list('fixture_id', flat=True)

    pending_reports = Fixture.objects.filter(
        pk__in=centre_fixture_ids,
        match_date__lt=today,
        status='completed',
    ).exclude(
        match_report__status__in=[MatchReportStatus.SUBMITTED, MatchReportStatus.APPROVED]
    ).select_related('home_team', 'away_team')

    draft_reports = MatchReport.objects.filter(
        referee=profile, status=MatchReportStatus.DRAFT,
    ).select_related('fixture__home_team', 'fixture__away_team')

    returned_reports = MatchReport.objects.filter(
        referee=profile, status=MatchReportStatus.RETURNED,
    ).select_related('fixture__home_team', 'fixture__away_team')

    # Squads awaiting approval (centre referee only)
    pending_squads = SquadSubmission.objects.filter(
        fixture_id__in=centre_fixture_ids,
        status=SquadStatus.SUBMITTED,
    ).select_related('fixture__home_team', 'fixture__away_team', 'team')

    # Availability for next 14 days
    upcoming_dates = [today + timedelta(days=i) for i in range(14)]
    availability_map = dict(
        RefereeAvailability.objects.filter(
            referee=profile,
            date__gte=today,
            date__lte=today + timedelta(days=13),
        ).values_list('date', 'status')
    )

    availability_calendar = []
    for d in upcoming_dates:
        availability_calendar.append({
            'date': d,
            'status': availability_map.get(d, None),
            'has_match': appointments.filter(fixture__match_date=d).exists(),
        })

    return render(request, 'portal/referee_dashboard.html', {
        'profile': profile,
        'pending_confirmation': pending_confirmation,
        'upcoming_matches': upcoming_matches,
        'current_matches': current_matches,
        'completed_matches': completed_matches[:10],
        'pending_reports': pending_reports,
        'draft_reports': draft_reports,
        'returned_reports': returned_reports,
        'pending_squads': pending_squads,
        'availability_calendar': availability_calendar,
        'total_appointments': appointments.count(),
    })


# ══════════════════════════════════════════════════════════════════════════════
#   REFEREE AVAILABILITY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@role_required('referee')
def referee_availability_view(request):
    """
    Referee sets availability for the next 30 days — calendar grid interface.
    POST toggles a single date's availability.
    """
    user = request.user
    try:
        profile = user.referee_profile
    except RefereeProfile.DoesNotExist:
        messages.error(request, 'No referee profile found.')
        return redirect('dashboard')

    today = date.today()
    date_range_end = today + timedelta(days=30)

    if request.method == 'POST':
        target_date_str = request.POST.get('date')
        new_status = request.POST.get('status')  # 'available' or 'unavailable'
        notes = request.POST.get('notes', '')

        if target_date_str and new_status in ('available', 'unavailable'):
            try:
                target_date = date.fromisoformat(target_date_str)
                if target_date >= today:
                    RefereeAvailability.objects.update_or_create(
                        referee=profile,
                        date=target_date,
                        defaults={'status': new_status, 'notes': notes},
                    )
                    status_label = 'Available' if new_status == 'available' else 'Unavailable'
                    messages.success(request, f'{status_label} set for {target_date.strftime("%d %b %Y")}.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid date.')

        return redirect('referee_availability')

    # Build 30-day calendar
    all_dates = [today + timedelta(days=i) for i in range(31)]
    availability_map = dict(
        RefereeAvailability.objects.filter(
            referee=profile,
            date__gte=today,
            date__lte=date_range_end,
        ).values_list('date', 'status')
    )
    notes_map = dict(
        RefereeAvailability.objects.filter(
            referee=profile,
            date__gte=today,
            date__lte=date_range_end,
        ).values_list('date', 'notes')
    )

    # Match dates this referee is appointed to
    match_dates = set(
        RefereeAppointment.objects.filter(
            referee=profile,
            fixture__match_date__gte=today,
            fixture__match_date__lte=date_range_end,
        ).values_list('fixture__match_date', flat=True)
    )

    calendar_days = []
    for d in all_dates:
        calendar_days.append({
            'date': d,
            'status': availability_map.get(d, None),
            'notes': notes_map.get(d, ''),
            'has_match': d in match_dates,
            'is_today': d == today,
            'weekday': d.strftime('%a'),
        })

    return render(request, 'portal/referee_availability.html', {
        'calendar_days': calendar_days,
        'profile': profile,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   TREASURER PORTAL
# ══════════════════════════════════════════════════════════════════════════════

@role_required('treasurer', 'admin')
def treasurer_dashboard_view(request):
    """Treasurer home — overview of pending, paid, and approved teams."""
    pending_count   = Team.objects.filter(status='pending', payment_confirmed=False).count()
    paid_count      = Team.objects.filter(status='pending', payment_confirmed=True).count()
    approved_count  = Team.objects.filter(status='registered').count()
    rejected_count  = Team.objects.filter(status='suspended').count()
    recent = Team.objects.filter(status='pending').order_by('-registered_at')[:5]
    return render(request, 'portal/treasurer/dashboard.html', {
        'pending_count':    pending_count,
        'paid_count':       paid_count,
        'approved_count':   approved_count,
        'rejected_count':   rejected_count,
        'recent_teams':     recent,
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


@role_required('treasurer', 'admin')
def treasurer_teams_view(request):
    """
    Treasurer main workspace:
    - Shows all pending teams
    - Treasurer can confirm payment (enter M-Pesa ref + amount)
    - Then approve → team status = registered, manager account created
    - Or reject the registration
    """
    if request.method == 'POST':
        team_id = request.POST.get('team_id')
        action  = request.POST.get('action')
        team    = get_object_or_404(Team, pk=team_id)

        if action == 'confirm_payment':
            ref    = request.POST.get('payment_reference', '').strip()
            amount = request.POST.get('payment_amount', '').strip()
            if not ref:
                messages.error(request, 'Please enter the M-Pesa / payment reference.')
            else:
                team.payment_confirmed    = True
                team.payment_reference    = ref
                # Default to the standard county fee if not entered
                team.payment_amount       = amount if amount else COUNTY_REGISTRATION_FEE_CAP
                team.payment_confirmed_by = request.user
                team.payment_confirmed_at = timezone.now()
                team.save()
                # Log this action explicitly for audit
                from admin_dashboard.models import ActivityLog as AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action='PAYMENT_VERIFIED',
                    description=f'{request.user.get_full_name()} confirmed payment for {team.name} (Ref: {ref}, Amount: {team.payment_amount})',
                    object_repr=str(team),
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
                messages.success(request, f'✅ Payment confirmed for <strong>{team.name}</strong> (Ref: {ref})')

        elif action == 'approve':
            if not team.payment_confirmed:
                messages.error(request, f'❌ Cannot approve {team.name} — payment not yet confirmed.')
            else:
                team.status = 'registered'
                team.save()
                # Create team manager account if email provided and no manager yet
                if team.contact_email and not team.manager:
                    try:
                        temp_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                        manager = User.objects.create_user(
                            email=team.contact_email,
                            password=temp_pw,
                            first_name=team.name,
                            last_name='Manager',
                            role=UserRole.TEAM_MANAGER,
                            county=team.county,
                        )
                        team.manager = manager
                        team.save()
                        messages.success(request, mark_safe(
                            f'✅ <strong>{team.name}</strong> approved!<br>'
                            f'Manager login: <code>{team.contact_email}</code><br>'
                            f'Temporary password: <code>{temp_pw}</code><br>'
                            f'<em>Share these credentials with the team manager.</em>'
                        ))
                    except Exception as e:
                        messages.warning(request, f'Team approved but manager account failed: {e}')
                else:
                    messages.success(request, f'✅ {team.name} approved.')

        elif action == 'reject':
            team.status = 'suspended'
            team.save()
            # Log rejection for audit
            from admin_dashboard.models import ActivityLog as AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='TEAM_REJECT',
                description=f'{request.user.get_full_name()} rejected team registration: {team.name}',
                object_repr=str(team),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            messages.warning(request, f'❌ {team.name} registration rejected.')

        return redirect('treasurer_teams')

    # Split pending teams into: not-yet-paid vs payment-confirmed-awaiting-approval
    unpaid  = Team.objects.filter(status='pending', payment_confirmed=False).order_by('-registered_at')
    paid    = Team.objects.filter(status='pending', payment_confirmed=True).order_by('-registered_at')
    return render(request, 'portal/treasurer/teams.html', {
        'unpaid_teams':         unpaid,
        'paid_teams':           paid,
        'unpaid_count':         unpaid.count(),
        'paid_count':           paid.count(),
        'registration_fee':     COUNTY_REGISTRATION_FEE_CAP,
    })
