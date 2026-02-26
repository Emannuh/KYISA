"""
KYISA CMS — Web Frontend Views (Template-Based Portals)
Includes both public website pages and authenticated CMS portal views.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from accounts.models import User, KenyaCounty
from competitions.models import Competition, Fixture
from teams.models import Team, Player
from referees.models import RefereeProfile, RefereeAppointment
from matches.models import MatchReport, SquadSubmission


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
        'referees': RefereeProfile.objects.filter(is_approved=True).count(),
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
    """Public competitions listing — active, upcoming, completed."""
    active = Competition.objects.filter(status='active')
    upcoming = Competition.objects.filter(status__in=['upcoming', 'registration'])
    completed = Competition.objects.filter(status='completed')
    return render(request, 'public/competitions.html', {
        'active_page': 'competitions',
        'active_competitions': active,
        'upcoming_competitions': upcoming,
        'completed_competitions': completed,
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
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard')
        else:
            return render(request, 'accounts/login.html', {
                'error': 'Invalid email or password. Please try again.',
                'email': email,
            })

    return render(request, 'accounts/login.html')


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
    if user.role == 'team_manager':
        stats['teams'] = Team.objects.filter(manager=user).count()
        my_teams = Team.objects.filter(manager=user)
        recent_fixtures = Fixture.objects.filter(
            home_team__in=my_teams
        ).union(
            Fixture.objects.filter(away_team__in=my_teams)
        ).order_by('-match_date')[:10]
    elif user.role == 'referee':
        try:
            profile = user.referee_profile
            recent_fixtures = Fixture.objects.filter(
                referee_appointments__referee=profile
            ).order_by('-match_date')[:10]
        except RefereeProfile.DoesNotExist:
            recent_fixtures = Fixture.objects.none()
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
    """Team detail with players."""
    team = get_object_or_404(Team, pk=pk)
    players = Player.objects.filter(team=team)
    return render(request, 'teams/detail.html', {
        'team': team,
        'players': players,
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
    """List fixtures and match reports."""
    user = request.user

    if user.role == 'team_manager':
        my_teams = Team.objects.filter(manager=user)
        fixtures = Fixture.objects.filter(
            home_team__in=my_teams
        ).union(
            Fixture.objects.filter(away_team__in=my_teams)
        ).order_by('-match_date')
    elif user.role == 'referee':
        try:
            fixtures = Fixture.objects.filter(
                referee_appointments__referee=user.referee_profile
            ).order_by('-match_date')
        except RefereeProfile.DoesNotExist:
            fixtures = Fixture.objects.none()
    else:
        fixtures = Fixture.objects.select_related(
            'competition', 'home_team', 'away_team', 'venue'
        ).order_by('-match_date')

    match_reports = MatchReport.objects.select_related(
        'fixture', 'referee'
    ).order_by('-submitted_at')[:20]

    return render(request, 'matches/list.html', {
        'fixtures': fixtures,
        'match_reports': match_reports,
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
            request.user.save()
            login(request, request.user)
            messages.success(request, 'Password updated successfully!')

    return redirect('web_profile')
