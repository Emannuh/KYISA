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
from competitions.models import (
    Competition, Fixture, SportType, EXHIBITION_SPORTS, COUNTY_REGISTRATION_FEE_CAP,
    CountyPayment, PaymentStatus, CompetitionStatus,
)
from teams.models import (
    Team, Player, VerificationStatus, RejectionReason, PLAYER_MIN_AGE, PLAYER_MAX_AGE,
    CountyRegistration, CountyRegStatus, CountyDiscipline, CountyPlayer, SQUAD_LIMITS,
    TechnicalBenchMember, TechnicalBenchRole, PlayerStatus,
)
from teams.forms import (
    PlayerRegistrationForm,
    CountyAdminRegistrationForm, CountyPaymentForm, CountyPlayerForm,
    TechnicalBenchForm,
)
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


def leadership_view(request):
    """Public leadership page — KYISA officials and their messages."""
    leaders = [
        {
            'name': 'Ambrose Kisoi',
            'title': 'Secretary General',
            'image': 'img/leadership/ambrose_kisoi.jpg',
            'message': (
                'Welcome to the Kenya Youth Intercounty Sports Association. '
                'As Secretary General, it is my privilege to lead an organisation '
                'that is dedicated to nurturing the next generation of Kenyan '
                'sporting talent. KYISA exists to provide a platform where young '
                'athletes from all 47 counties can showcase their abilities, '
                'build lifelong friendships, and develop the discipline that '
                'sport instils.\n\n'
                'Our annual championship has grown into one of Kenya\'s most '
                'anticipated youth sporting events, bringing together thousands '
                'of talented young men and women aged 18 to 23. We believe that '
                'every county has untapped potential, and through fair, '
                'competitive, and well-organised tournaments, we aim to uncover '
                'and develop that talent.\n\n'
                'I invite you to explore our programmes, follow our competitions, '
                'and join us in building a stronger, more united Kenya through sport.'
            ),
            'has_photo': True,
        },
        {
            'name': 'Chairman',
            'title': 'Chairman',
            'image': None,
            'message': None,
            'has_photo': False,
            'placeholder': True,
        },
        {
            'name': 'Vice Chairman',
            'title': 'Vice Chairman',
            'image': None,
            'message': None,
            'has_photo': False,
            'placeholder': True,
        },
        {
            'name': 'Treasurer',
            'title': 'Treasurer',
            'image': None,
            'message': None,
            'has_photo': False,
            'placeholder': True,
        },
    ]
    return render(request, 'public/leadership.html', {
        'active_page': 'leadership',
        'leaders': leaders,
    })


def public_competitions_view(request):
    """Public competitions listing — grouped by sport, with exhibition marker."""
    all_comps = Competition.objects.all()
    active    = all_comps.filter(status='active')
    upcoming  = all_comps.filter(status__in=['upcoming', 'registration'])
    completed = all_comps.filter(status='completed')

    # Flat catalogue — used for per-sport competition sections
    SPORT_CATALOGUE = [
        {'key': SportType.FOOTBALL_MEN,       'label': 'Football (Men)',          'icon': '\u26BD', 'exhibition': False},
        {'key': SportType.FOOTBALL_WOMEN,     'label': 'Football (Women)',        'icon': '\u26BD', 'exhibition': False},
        {'key': SportType.VOLLEYBALL_MEN,     'label': 'Volleyball (Men)',        'icon': '\U0001F3D0', 'exhibition': False},
        {'key': SportType.VOLLEYBALL_WOMEN,   'label': 'Volleyball (Women)',      'icon': '\U0001F3D0', 'exhibition': False},
        {'key': SportType.BASKETBALL_MEN,     'label': 'Basketball 5\u00D75 (Men)',   'icon': '\U0001F3C0', 'exhibition': False},
        {'key': SportType.BASKETBALL_WOMEN,   'label': 'Basketball 5\u00D75 (Women)', 'icon': '\U0001F3C0', 'exhibition': False},
        {'key': SportType.BASKETBALL_3X3_MEN,   'label': 'Basketball 3\u00D73 (Men)',   'icon': '\U0001F3C0', 'exhibition': False},
        {'key': SportType.BASKETBALL_3X3_WOMEN, 'label': 'Basketball 3\u00D73 (Women)', 'icon': '\U0001F3C0', 'exhibition': False},
        {'key': SportType.HANDBALL_MEN,       'label': 'Handball (Men)',          'icon': '\U0001F93E', 'exhibition': False},
        {'key': SportType.HANDBALL_WOMEN,     'label': 'Handball (Women)',        'icon': '\U0001F93E', 'exhibition': False},
    ]

    # Grouped disciplines — for the top tile grid with dropdowns
    DISCIPLINES = [
        {
            'name': 'Football', 'icon': '\u26BD', 'exhibition': False,
            'variants': [
                {'key': SportType.FOOTBALL_MEN,   'label': 'Men'},
                {'key': SportType.FOOTBALL_WOMEN, 'label': 'Women'},
            ],
        },
        {
            'name': 'Volleyball', 'icon': '\U0001F3D0', 'exhibition': False,
            'variants': [
                {'key': SportType.VOLLEYBALL_MEN,   'label': 'Men'},
                {'key': SportType.VOLLEYBALL_WOMEN, 'label': 'Women'},
            ],
        },
        {
            'name': 'Basketball 5\u00D75', 'icon': '\U0001F3C0', 'exhibition': False,
            'variants': [
                {'key': SportType.BASKETBALL_MEN,   'label': 'Men'},
                {'key': SportType.BASKETBALL_WOMEN, 'label': 'Women'},
            ],
        },
        {
            'name': 'Basketball 3\u00D73', 'icon': '\U0001F3C0', 'exhibition': False,
            'variants': [
                {'key': SportType.BASKETBALL_3X3_MEN,   'label': 'Men'},
                {'key': SportType.BASKETBALL_3X3_WOMEN, 'label': 'Women'},
            ],
        },
        {
            'name': 'Handball', 'icon': '\U0001F93E', 'exhibition': False,
            'variants': [
                {'key': SportType.HANDBALL_MEN,   'label': 'Men'},
                {'key': SportType.HANDBALL_WOMEN, 'label': 'Women'},
            ],
        },
    ]

    return render(request, 'public/competitions.html', {
        'active_page': 'competitions',
        'active_competitions': active,
        'upcoming_competitions': upcoming,
        'completed_competitions': completed,
        'sport_catalogue': SPORT_CATALOGUE,
        'disciplines': DISCIPLINES,
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
    """Public results page — completed matches, upcoming fixtures, and competition links."""
    now = timezone.now()
    sport_filter = request.GET.get('sport', '').strip()
    valid_sports = {c.value for c in SportType}
    sport_filter = sport_filter if sport_filter in valid_sports else ''

    completed_qs = Fixture.objects.filter(status='completed')
    upcoming_qs = Fixture.objects.filter(match_date__gte=now).exclude(status='completed')
    active_comps_qs = Competition.objects.filter(status__in=['active', 'group_stage', 'knockout'])
    completed_comps_qs = Competition.objects.filter(status='completed')

    if sport_filter:
        completed_qs = completed_qs.filter(competition__sport_type=sport_filter)
        upcoming_qs = upcoming_qs.filter(competition__sport_type=sport_filter)
        active_comps_qs = active_comps_qs.filter(sport_type=sport_filter)
        completed_comps_qs = completed_comps_qs.filter(sport_type=sport_filter)

    completed = completed_qs.select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('-match_date')[:30]

    upcoming = upcoming_qs.select_related(
        'competition', 'home_team', 'away_team', 'venue'
    ).order_by('match_date')[:15]

    active_competitions = active_comps_qs.order_by('name')
    completed_competitions = completed_comps_qs.order_by('-end_date')[:10]

    # Build display label for active filter
    sport_display = ''
    if sport_filter:
        sport_display = dict(SportType.choices).get(sport_filter, sport_filter)

    return render(request, 'public/results.html', {
        'active_page': 'results',
        'completed_fixtures': completed,
        'upcoming_fixtures': upcoming,
        'active_competitions': active_competitions,
        'completed_competitions': completed_competitions,
        'sport_filter': sport_filter,
        'sport_display': sport_display,
        'sport_choices': SportType.choices,
    })


def public_statistics_view(request):
    """
    Public statistics hub — top scorers, assist leaders, disciplinary,
    and clean sheet leaders across all active/completed competitions.
    Users can filter by competition.
    """
    from competitions.models import Pool, PoolTeam
    from matches.models import PlayerStatistics
    from matches.stats_engine import (
        get_top_scorers, get_top_assisters,
        get_disciplinary_table, get_clean_sheet_leaders,
    )
    from django.db.models import F, Sum

    # Competitions available for filtering
    competitions = Competition.objects.filter(
        status__in=['active', 'group_stage', 'knockout', 'completed']
    ).order_by('-start_date')

    # Optional competition filter
    comp_id = request.GET.get('competition', '')
    selected_competition = None

    if comp_id:
        try:
            selected_competition = Competition.objects.get(pk=comp_id)
        except Competition.DoesNotExist:
            pass

    if selected_competition:
        top_scorers = get_top_scorers(selected_competition, limit=20)
        top_assisters = get_top_assisters(selected_competition, limit=20)
        disciplinary = get_disciplinary_table(selected_competition, limit=20)
        clean_sheets = get_clean_sheet_leaders(selected_competition, limit=10)
    else:
        # Aggregate across all active/completed competitions
        top_scorers = PlayerStatistics.objects.filter(
            goals__gt=0,
            competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
        ).select_related('player', 'team', 'competition').order_by('-goals', '-assists')[:20]

        top_assisters = PlayerStatistics.objects.filter(
            assists__gt=0,
            competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
        ).select_related('player', 'team', 'competition').order_by('-assists', '-goals')[:20]

        disciplinary = PlayerStatistics.objects.filter(
            competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
        ).annotate(
            total_cards=F('yellow_cards') + F('red_cards')
        ).filter(total_cards__gt=0).select_related(
            'player', 'team', 'competition'
        ).order_by('-red_cards', '-yellow_cards')[:20]

        clean_sheets = PlayerStatistics.objects.filter(
            clean_sheets__gt=0,
            player__position='GK',
            competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
        ).select_related('player', 'team', 'competition').order_by('-clean_sheets')[:10]

    # Summary stats
    total_goals = PlayerStatistics.objects.filter(
        competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
    ).aggregate(total=Sum('goals'))['total'] or 0
    total_matches = Fixture.objects.filter(status='completed').count()
    total_cards = PlayerStatistics.objects.filter(
        competition__status__in=['active', 'group_stage', 'knockout', 'completed'],
    ).aggregate(
        yellows=Sum('yellow_cards'),
        reds=Sum('red_cards'),
    )

    return render(request, 'public/statistics.html', {
        'active_page': 'results',
        'competitions': competitions,
        'selected_competition': selected_competition,
        'top_scorers': top_scorers,
        'top_assisters': top_assisters,
        'disciplinary': disciplinary,
        'clean_sheets': clean_sheets,
        'total_goals': total_goals,
        'total_matches': total_matches,
        'total_yellows': total_cards['yellows'] or 0,
        'total_reds': total_cards['reds'] or 0,
    })


def public_competition_standings_view(request, pk):
    """
    Public competition standings — pool tables, knockout bracket, and top stats.
    Auto-updated from approved match reports.
    """
    from competitions.models import Pool, PoolTeam, KnockoutRound
    from matches.stats_engine import (
        get_top_scorers, get_top_assisters,
        get_disciplinary_table, get_clean_sheet_leaders,
    )

    competition = get_object_or_404(Competition, pk=pk)

    # Pool standings
    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team'
    ).order_by('name')

    pool_standings = []
    for pool in pools:
        teams = pool.pool_teams.select_related('team').all()
        sorted_teams = sorted(
            teams,
            key=lambda pt: (pt.points, pt.goal_difference, pt.goals_for),
            reverse=True,
        )
        pool_standings.append({'pool': pool, 'teams': sorted_teams})

    # Knockout bracket
    knockout_fixtures = Fixture.objects.filter(
        competition=competition, is_knockout=True
    ).select_related(
        'home_team', 'away_team', 'venue', 'winner'
    ).order_by('knockout_round', 'bracket_position', 'match_date')

    knockout_rounds = {}
    for f in knockout_fixtures:
        round_name = f.get_knockout_round_display() if f.knockout_round else 'Unknown'
        if round_name not in knockout_rounds:
            knockout_rounds[round_name] = []
        knockout_rounds[round_name].append(f)

    # Recent results for this competition
    recent_results = Fixture.objects.filter(
        competition=competition, status='completed'
    ).select_related('home_team', 'away_team', 'venue').order_by('-match_date')[:10]

    # Upcoming fixtures
    upcoming = Fixture.objects.filter(
        competition=competition,
        match_date__gte=timezone.now(),
    ).exclude(status='completed').select_related(
        'home_team', 'away_team', 'venue'
    ).order_by('match_date')[:10]

    # Statistics
    top_scorers = get_top_scorers(competition, limit=10)
    top_assisters = get_top_assisters(competition, limit=10)
    disciplinary = get_disciplinary_table(competition, limit=10)
    clean_sheets = get_clean_sheet_leaders(competition, limit=5)

    return render(request, 'public/competition_standings.html', {
        'active_page': 'results',
        'competition': competition,
        'pool_standings': pool_standings,
        'knockout_rounds': knockout_rounds,
        'recent_results': recent_results,
        'upcoming_fixtures': upcoming,
        'top_scorers': top_scorers,
        'top_assisters': top_assisters,
        'disciplinary': disciplinary,
        'clean_sheets': clean_sheets,
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

    if user.role == 'competition_manager':
        return redirect('cm_dashboard')

    if user.role == 'county_sports_admin':
        return redirect('county_admin_dashboard')

    if user.role == 'team_manager':
        return redirect('team_manager_dashboard')

    if user.role == 'secretary_general':
        return redirect('sg_dashboard')

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

                # ── Auto-trigger FIFA Connect pre-screening ──────────────
                try:
                    from teams.fifa_connect_service import FIFAConnectService
                    from teams.models import FIFAConnectStatus, PlayerVerificationLog, VerificationStep
                    svc = FIFAConnectService()
                    fc_result = svc.check_player(player)
                    if fc_result.is_flagged:
                        player.fifa_connect_status = FIFAConnectStatus.FLAGGED
                        player.fifa_connect_leagues = fc_result.leagues_found
                        player.fifa_connect_notes = fc_result.flag_reason
                        if fc_result.fifa_connect_id:
                            player.fifa_connect_id = fc_result.fifa_connect_id
                        player.save()
                        PlayerVerificationLog.objects.create(
                            player=player,
                            step=VerificationStep.FIFA_CONNECT,
                            action='auto_screen_on_add',
                            result='flagged',
                            details={'leagues_found': fc_result.leagues_found},
                            notes=fc_result.flag_reason,
                        )
                        messages.warning(request, (
                            f'🚩 FIFA Connect WARNING: {player.get_full_name()} '
                            f'may be registered in a higher-level league. '
                            f'Requires clearance review before participation.'
                        ))
                    elif fc_result.is_clear:
                        player.fifa_connect_status = FIFAConnectStatus.CLEAR
                        if fc_result.fifa_connect_id:
                            player.fifa_connect_id = fc_result.fifa_connect_id
                        player.fifa_connect_notes = "Auto-screened on registration — clear."
                        player.save()
                except Exception:
                    pass  # Don't block player registration on API errors

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
    """Deprecated — team registration is now handled via county registration."""
    return redirect('county_admin_register')


def team_register_success_view(request):
    """Deprecated — redirects to county registration."""
    return redirect('county_admin_register')


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

@role_required('admin', 'competition_manager', 'secretary_general')
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
            # Log to audit trail
            from teams.models import PlayerVerificationLog, VerificationStep
            PlayerVerificationLog.objects.create(
                player=player, step=VerificationStep.DOCUMENT,
                action='verified', result='verified',
                notes='Documents verified by admin.',
                performed_by=request.user,
            )
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
            from teams.models import PlayerVerificationLog, VerificationStep
            PlayerVerificationLog.objects.create(
                player=player, step=VerificationStep.DOCUMENT,
                action='rejected', result='rejected',
                details={'reason': reason},
                notes=notes,
                performed_by=request.user,
            )
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
            from teams.models import PlayerVerificationLog, VerificationStep
            PlayerVerificationLog.objects.create(
                player=player, step=VerificationStep.DOCUMENT,
                action='reset', result='pending',
                notes='Reset to pending by admin.',
                performed_by=request.user,
            )
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

    # Only FULLY CLEARED players (docs verified + Huduma verified + FIFA Connect clear + eligible status)
    players = Player.objects.filter(
        team=team, status='eligible', verification_status='verified',
        huduma_status='verified', fifa_connect_status='clear',
    ).order_by('shirt_number')

    # Also get partially-cleared players for information
    partially_cleared = Player.objects.filter(
        team=team, status='eligible', verification_status='verified',
    ).exclude(
        huduma_status='verified', fifa_connect_status='clear',
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

            # Auto-update pool standings + player statistics
            from matches.stats_engine import process_approved_report
            process_approved_report(report)

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
    """Treasurer home — overview of county payments, teams, and registration status."""
    current_season = str(date.today().year)

    # County payment stats
    county_payments = CountyPayment.objects.filter(season=current_season)
    counties_paid = county_payments.filter(payment_status__in=['paid', 'waived']).count()
    counties_pending = county_payments.filter(payment_status='pending').count()
    total_collected = sum(
        cp.participation_fee for cp in county_payments
        if cp.payment_status in ('paid', 'waived')
    )

    # Team stats
    pending_count   = Team.objects.filter(status='pending', payment_confirmed=False).count()
    paid_count      = Team.objects.filter(status='pending', payment_confirmed=True).count()
    approved_count  = Team.objects.filter(status='registered').count()
    rejected_count  = Team.objects.filter(status='suspended').count()

    # Recent pending teams
    recent = Team.objects.filter(status='pending').order_by('-registered_at')[:5]
    # Recent county payments
    recent_payments = county_payments.order_by('-updated_at')[:5]

    return render(request, 'portal/treasurer/dashboard.html', {
        'pending_count':    pending_count,
        'paid_count':       paid_count,
        'approved_count':   approved_count,
        'rejected_count':   rejected_count,
        'recent_teams':     recent,
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
        'counties_paid':    counties_paid,
        'counties_pending': counties_pending,
        'total_collected':  total_collected,
        'recent_payments':  recent_payments,
        'current_season':   current_season,
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
                
                # Send payment receipt notification
                from teams.notifications import send_payment_receipt
                send_payment_receipt(team, request.user)
                
                # Log this action explicitly for audit
                from admin_dashboard.models import ActivityLog as AuditLog
                AuditLog.objects.create(
                    user=request.user,
                    action='PAYMENT_VERIFIED',
                    description=f'{request.user.get_full_name()} confirmed payment for {team.name} (Ref: {ref}, Amount: {team.payment_amount})',
                    object_repr=str(team),
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
                messages.success(request, f'✅ Payment confirmed for <strong>{team.name}</strong> (Ref: {ref}). Receipt sent to sports officer and team contact.')

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


@role_required('treasurer', 'admin')
def treasurer_county_payments_view(request):
    """
    Treasurer manages county-level payments.
    Each county pays KSh 250,000 per season to cover ALL sports.
    """
    current_season = str(date.today().year)
    season = request.GET.get('season', current_season)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_county':
            county = request.POST.get('county', '').strip()
            if not county:
                messages.error(request, 'Please select a county.')
            elif CountyPayment.objects.filter(county=county, season=season).exists():
                messages.warning(request, f'{county} already has a payment record for {season}.')
            else:
                CountyPayment.objects.create(
                    county=county,
                    season=season,
                    participation_fee=COUNTY_REGISTRATION_FEE_CAP,
                )
                messages.success(request, f'County payment record created for {county} ({season}).')

        elif action == 'confirm_payment':
            payment_id = request.POST.get('payment_id')
            ref = request.POST.get('payment_reference', '').strip()
            payment_date_str = request.POST.get('payment_date', '').strip()
            notes = request.POST.get('notes', '').strip()

            if not ref:
                messages.error(request, 'Please enter the M-Pesa / payment reference.')
            else:
                try:
                    cp = CountyPayment.objects.get(pk=payment_id)
                    cp.payment_status = PaymentStatus.PAID
                    cp.payment_reference = ref
                    cp.confirmed_by = request.user
                    cp.confirmed_at = timezone.now()
                    cp.notes = notes
                    if payment_date_str:
                        from datetime import datetime as dt
                        cp.payment_date = dt.strptime(payment_date_str, '%Y-%m-%d').date()
                    else:
                        cp.payment_date = date.today()
                    cp.save()

                    # Also unlock all teams from this county
                    Team.objects.filter(
                        county=cp.county, payment_confirmed=False
                    ).update(
                        payment_confirmed=True,
                        payment_reference=ref,
                        payment_amount=COUNTY_REGISTRATION_FEE_CAP,
                        payment_confirmed_by=request.user,
                        payment_confirmed_at=timezone.now(),
                    )

                    # Audit log
                    from admin_dashboard.models import ActivityLog as AuditLog
                    AuditLog.objects.create(
                        user=request.user,
                        action='COUNTY_PAYMENT_CONFIRMED',
                        description=(
                            f'{request.user.get_full_name()} confirmed county payment for '
                            f'{cp.county} — Season {season} (Ref: {ref})'
                        ),
                        object_repr=str(cp),
                        ip_address=request.META.get('REMOTE_ADDR', ''),
                    )
                    messages.success(request, f'Payment confirmed for {cp.county} (Ref: {ref}).')
                except CountyPayment.DoesNotExist:
                    messages.error(request, 'Payment record not found.')

        elif action == 'waive_payment':
            payment_id = request.POST.get('payment_id')
            notes = request.POST.get('notes', '').strip()
            try:
                cp = CountyPayment.objects.get(pk=payment_id)
                cp.payment_status = PaymentStatus.WAIVED
                cp.confirmed_by = request.user
                cp.confirmed_at = timezone.now()
                cp.notes = notes or 'Payment waived'
                cp.save()

                # Unlock teams
                Team.objects.filter(
                    county=cp.county, payment_confirmed=False
                ).update(
                    payment_confirmed=True,
                    payment_confirmed_by=request.user,
                    payment_confirmed_at=timezone.now(),
                )

                messages.success(request, f'Payment waived for {cp.county}.')
            except CountyPayment.DoesNotExist:
                messages.error(request, 'Payment record not found.')

        return redirect('treasurer_county_payments')

    county_payments = CountyPayment.objects.filter(season=season).order_by('county')
    paid = county_payments.filter(payment_status__in=['paid', 'waived'])
    pending = county_payments.filter(payment_status='pending')

    # Counties from KenyaCounty enum that don't have a payment record yet
    existing_counties = set(county_payments.values_list('county', flat=True))
    available_counties = [
        (c.value, c.label) for c in KenyaCounty
        if c.value not in existing_counties
    ]

    return render(request, 'portal/treasurer/county_payments.html', {
        'paid_payments':       paid,
        'pending_payments':    pending,
        'paid_count':          paid.count(),
        'pending_count':       pending.count(),
        'total_collected':     sum(cp.participation_fee for cp in paid),
        'registration_fee':    COUNTY_REGISTRATION_FEE_CAP,
        'season':              season,
        'current_season':      current_season,
        'available_counties':  available_counties,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COMPETITION MANAGER — STATISTICS & LEADERBOARDS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('competition_manager', 'admin')
def competition_standings_view(request, pk):
    """
    Competition Manager view: full standings, knockout bracket, and statistics.
    """
    competition = get_object_or_404(Competition, pk=pk)
    from competitions.models import Pool, PoolTeam

    # Group standings
    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team'
    ).order_by('name')

    pool_standings = []
    for pool in pools:
        teams = pool.pool_teams.all().order_by('-won', 'lost')
        # Sort by points, then goal difference, then goals scored
        sorted_teams = sorted(
            teams,
            key=lambda pt: (pt.points, pt.goal_difference, pt.goals_for),
            reverse=True
        )
        pool_standings.append({
            'pool': pool,
            'teams': sorted_teams,
        })

    # Knockout fixtures
    from competitions.models import KnockoutRound
    knockout_fixtures = Fixture.objects.filter(
        competition=competition, is_knockout=True
    ).select_related('home_team', 'away_team', 'venue', 'winner').order_by(
        'knockout_round', 'bracket_position', 'match_date'
    )

    # Group knockout fixtures by round
    knockout_rounds = {}
    for f in knockout_fixtures:
        round_name = f.get_knockout_round_display() if f.knockout_round else 'Unknown'
        if round_name not in knockout_rounds:
            knockout_rounds[round_name] = []
        knockout_rounds[round_name].append(f)

    # Statistics
    from matches.stats_engine import (
        get_top_scorers, get_top_assisters,
        get_disciplinary_table, get_clean_sheet_leaders,
    )
    top_scorers = get_top_scorers(competition, limit=10)
    top_assisters = get_top_assisters(competition, limit=10)
    disciplinary = get_disciplinary_table(competition, limit=10)
    clean_sheets = get_clean_sheet_leaders(competition, limit=5)

    return render(request, 'portal/competition_standings.html', {
        'competition':      competition,
        'pool_standings':   pool_standings,
        'knockout_rounds':  knockout_rounds,
        'top_scorers':      top_scorers,
        'top_assisters':    top_assisters,
        'disciplinary':     disciplinary,
        'clean_sheets':     clean_sheets,
    })


@role_required('competition_manager', 'admin')
def competition_reports_view(request, pk):
    """
    Competition Manager reviews and approves match reports for a competition.
    """
    competition = get_object_or_404(Competition, pk=pk)
    filter_status = request.GET.get('status', 'submitted')

    reports_qs = MatchReport.objects.filter(
        fixture__competition=competition
    ).select_related(
        'fixture__home_team', 'fixture__away_team',
        'fixture__venue', 'referee__user'
    ).order_by('-submitted_at')

    if filter_status and filter_status != 'all':
        reports_qs = reports_qs.filter(status=filter_status)

    return render(request, 'portal/competition_reports.html', {
        'competition': competition,
        'reports': reports_qs,
        'filter_status': filter_status,
        'submitted_count': MatchReport.objects.filter(
            fixture__competition=competition, status='submitted'
        ).count(),
        'approved_count': MatchReport.objects.filter(
            fixture__competition=competition, status='approved'
        ).count(),
    })


@role_required('competition_manager', 'admin')
def competition_report_approve_view(request, pk, report_pk):
    """
    Competition Manager approves or returns a specific match report.
    On approval: updates fixture scores, pool standings, and player statistics.
    """
    competition = get_object_or_404(Competition, pk=pk)
    report = get_object_or_404(MatchReport, pk=report_pk, fixture__competition=competition)
    events = report.events.select_related('team', 'player').order_by('minute')

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('reviewer_notes', '')

        if action == 'approve':
            report.status = MatchReportStatus.APPROVED
            report.reviewed_by = request.user
            report.reviewed_at = timezone.now()
            report.reviewer_notes = notes

            # Update fixture
            fixture = report.fixture
            fixture.home_score = report.home_score
            fixture.away_score = report.away_score
            fixture.status = 'completed'
            fixture.save(update_fields=['home_score', 'away_score', 'status'])

            # Auto-update standings + player stats
            from matches.stats_engine import process_approved_report
            process_approved_report(report)

            report.save()

            # Audit log
            from admin_dashboard.models import ActivityLog as AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='MATCH_REPORT_APPROVED',
                description=(
                    f'{request.user.get_full_name()} approved match report: '
                    f'{fixture.home_team} {report.home_score}-{report.away_score} '
                    f'{fixture.away_team}'
                ),
                object_repr=str(report),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            messages.success(
                request,
                f'Match report approved — {fixture.home_team} '
                f'{report.home_score}-{report.away_score} {fixture.away_team}. '
                f'Standings and player statistics updated automatically.'
            )

        elif action == 'return':
            report.status = MatchReportStatus.RETURNED
            report.reviewer_notes = notes
            report.save()
            messages.warning(request, 'Match report returned for revision.')

        return redirect('competition_reports', pk=competition.pk)

    return render(request, 'portal/competition_report_approve.html', {
        'competition': competition,
        'report': report,
        'events': events,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   REFEREE MANAGER — MATCH APPOINTMENTS
# ══════════════════════════════════════════════════════════════════════════════

from referees.models import AppointmentRole, AppointmentStatus as ApptStatus


@role_required('referee_manager', 'admin')
def referee_appointments_view(request):
    """
    Referee Manager — overview of all fixtures that need officials,
    summary statistics and appointment status per match.
    """
    today = date.today()
    filter_status = request.GET.get('status', 'upcoming')  # upcoming | all | past

    # Base queryset: upcoming confirmed/pending fixtures
    fixtures_qs = Fixture.objects.select_related(
        'competition', 'home_team', 'away_team', 'venue',
    ).prefetch_related('referee_appointments__referee__user')

    if filter_status == 'upcoming':
        fixtures_qs = fixtures_qs.filter(match_date__gte=today).exclude(status__in=['cancelled'])
    elif filter_status == 'past':
        fixtures_qs = fixtures_qs.filter(match_date__lt=today)
    else:
        fixtures_qs = fixtures_qs.all()

    fixtures_qs = fixtures_qs.order_by('match_date', 'kickoff_time')

    # Build enriched list
    REQUIRED_ROLES = ['centre', 'ar1', 'ar2', 'fourth']
    fixture_data = []
    total_needing = 0
    total_fully_appointed = 0
    total_partially = 0

    for fixture in fixtures_qs:
        appointments = {a.role: a for a in fixture.referee_appointments.all()}
        roles_info = []
        filled = 0
        for role_key in REQUIRED_ROLES:
            appt = appointments.get(role_key)
            roles_info.append({
                'role_key': role_key,
                'role_label': dict(AppointmentRole.choices).get(role_key, role_key),
                'appointment': appt,
                'referee_name': appt.referee.user.get_full_name() if appt else None,
                'status': appt.status if appt else None,
                'status_display': appt.get_status_display() if appt else 'Not Appointed',
            })
            if appt:
                filled += 1

        needs_officials = filled < len(REQUIRED_ROLES)
        is_fully_appointed = filled == len(REQUIRED_ROLES)

        if needs_officials:
            total_needing += 1
        if is_fully_appointed:
            total_fully_appointed += 1
        elif filled > 0:
            total_partially += 1

        fixture_data.append({
            'fixture': fixture,
            'roles': roles_info,
            'filled': filled,
            'total_roles': len(REQUIRED_ROLES),
            'needs_officials': needs_officials,
            'is_fully_appointed': is_fully_appointed,
        })

    # Summary stats
    approved_referees_count = RefereeProfile.objects.filter(is_approved=True).count()

    return render(request, 'portal/referee_appointments.html', {
        'fixture_data': fixture_data,
        'filter_status': filter_status,
        'total_fixtures': len(fixture_data),
        'total_needing': total_needing,
        'total_fully_appointed': total_fully_appointed,
        'total_partially': total_partially,
        'approved_referees_count': approved_referees_count,
    })


@role_required('referee_manager', 'admin')
def referee_appoint_view(request, fixture_pk):
    """
    Referee Manager appoints officials to a specific fixture.
    Shows fixture info, current appointments, and forms to assign each role.
    """
    fixture = get_object_or_404(
        Fixture.objects.select_related(
            'competition', 'home_team', 'away_team', 'venue',
        ),
        pk=fixture_pk,
    )
    today = date.today()

    REQUIRED_ROLES = ['centre', 'ar1', 'ar2', 'fourth']
    role_labels = dict(AppointmentRole.choices)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'appoint':
            role = request.POST.get('role', '')
            referee_id = request.POST.get('referee_id', '')
            notes = request.POST.get('notes', '')

            if role not in REQUIRED_ROLES:
                messages.error(request, 'Invalid role.')
            elif not referee_id:
                messages.error(request, 'Please select a referee.')
            else:
                try:
                    referee_profile = RefereeProfile.objects.get(pk=referee_id, is_approved=True)
                except RefereeProfile.DoesNotExist:
                    messages.error(request, 'Selected referee not found or not approved.')
                    return redirect('referee_appoint', fixture_pk=fixture.pk)

                # Check for duplicate (same referee already appointed in this fixture for another role)
                existing_same_role = RefereeAppointment.objects.filter(
                    fixture=fixture, role=role
                ).exclude(status='replaced').first()

                if existing_same_role:
                    # Replace existing appointment
                    existing_same_role.status = 'replaced'
                    existing_same_role.save()

                # Check referee doesn't have a conflicting appointment on same date
                conflict = RefereeAppointment.objects.filter(
                    referee=referee_profile,
                    fixture__match_date=fixture.match_date,
                    status__in=['pending', 'confirmed'],
                ).exclude(fixture=fixture).first()

                if conflict:
                    messages.warning(
                        request,
                        f'⚠️ {referee_profile.user.get_full_name()} already has an appointment '
                        f'on {fixture.match_date.strftime("%d %b %Y")} '
                        f'({conflict.fixture}). Appointment created anyway — please verify.'
                    )

                # Create appointment
                RefereeAppointment.objects.create(
                    fixture=fixture,
                    referee=referee_profile,
                    role=role,
                    appointed_by=request.user,
                    notes=notes,
                )
                messages.success(
                    request,
                    f'✅ {referee_profile.user.get_full_name()} appointed as '
                    f'{role_labels.get(role, role)} for {fixture}.'
                )

        elif action == 'remove':
            appt_id = request.POST.get('appointment_id', '')
            try:
                appt = RefereeAppointment.objects.get(pk=appt_id, fixture=fixture)
                ref_name = appt.referee.user.get_full_name()
                role_display = appt.get_role_display()
                appt.status = 'replaced'
                appt.save()
                messages.success(request, f'🔄 {ref_name} ({role_display}) removed from this fixture.')
            except RefereeAppointment.DoesNotExist:
                messages.error(request, 'Appointment not found.')

        return redirect('referee_appoint', fixture_pk=fixture.pk)

    # ── Build role data ──
    current_appointments = {
        a.role: a for a in RefereeAppointment.objects.filter(
            fixture=fixture
        ).exclude(status='replaced').select_related('referee__user')
    }

    roles_data = []
    for role_key in REQUIRED_ROLES:
        appt = current_appointments.get(role_key)
        roles_data.append({
            'role_key': role_key,
            'role_label': role_labels.get(role_key, role_key),
            'appointment': appt,
            'referee_name': appt.referee.user.get_full_name() if appt else None,
            'status': appt.status if appt else None,
            'status_display': appt.get_status_display() if appt else None,
        })

    # ── Available referees (approved, with availability info for match date) ──
    approved_referees = RefereeProfile.objects.filter(
        is_approved=True
    ).select_related('user').order_by('user__last_name')

    # Get availability map for this date
    availability_map = dict(
        RefereeAvailability.objects.filter(
            referee__in=approved_referees,
            date=fixture.match_date,
        ).values_list('referee_id', 'status')
    )

    # Get appointments already on this match date (to flag busy referees)
    busy_on_date = set(
        RefereeAppointment.objects.filter(
            fixture__match_date=fixture.match_date,
            status__in=['pending', 'confirmed'],
        ).exclude(fixture=fixture).values_list('referee_id', flat=True)
    )

    # Already appointed to THIS fixture
    already_appointed_ids = set(
        a.referee_id for a in current_appointments.values()
    )

    referees_list = []
    for ref in approved_referees:
        avail = availability_map.get(ref.pk, None)
        is_busy = ref.pk in busy_on_date
        is_appointed_here = ref.pk in already_appointed_ids
        referees_list.append({
            'profile': ref,
            'full_name': ref.user.get_full_name(),
            'level': ref.get_level_display(),
            'county': ref.county,
            'total_matches': ref.total_matches,
            'avg_rating': ref.avg_rating,
            'availability': avail,
            'availability_label': (
                'Available' if avail == 'available'
                else 'Unavailable' if avail == 'unavailable'
                else 'Not Set'
            ),
            'is_busy': is_busy,
            'is_appointed_here': is_appointed_here,
        })

    return render(request, 'portal/referee_appoint.html', {
        'fixture': fixture,
        'roles_data': roles_data,
        'referees_list': referees_list,
        'required_roles': REQUIRED_ROLES,
        'role_labels': role_labels,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COMPETITION MANAGER — FULL PORTAL VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('competition_manager', 'admin')
def cm_dashboard_view(request):
    """Competition Manager dashboard — overview of all competitions and key stats."""
    from competitions.models import (
        Competition, Fixture, Venue, Pool, PoolTeam,
        SportType, CompetitionStatus, CountyPayment, PaymentStatus,
    )
    from matches.models import MatchReport

    competitions = Competition.objects.all()
    active = competitions.filter(status__in=['active', 'group_stage', 'knockout'])
    registration = competitions.filter(status='registration')

    # Key counts
    stats = {
        'total_competitions': competitions.count(),
        'active_competitions': active.count(),
        'total_fixtures': Fixture.objects.count(),
        'completed_fixtures': Fixture.objects.filter(status='completed').count(),
        'pending_reports': MatchReport.objects.filter(status='submitted').count(),
        'total_teams': Team.objects.filter(status='registered').count(),
        'total_venues': Venue.objects.filter(is_active=True).count(),
        'paid_counties': CountyPayment.objects.filter(
            payment_status__in=['paid', 'waived']
        ).count(),
    }

    # Recent fixture results
    recent_results = Fixture.objects.filter(
        status='completed'
    ).select_related(
        'competition', 'home_team', 'away_team'
    ).order_by('-updated_at')[:8]

    # Pending reports needing approval
    pending_reports = MatchReport.objects.filter(
        status='submitted'
    ).select_related(
        'fixture__competition', 'fixture__home_team', 'fixture__away_team',
        'referee__user'
    ).order_by('-submitted_at')[:5]

    # Sport breakdown
    sport_breakdown = []
    for sport_val, sport_label in SportType.choices:
        count = competitions.filter(sport_type=sport_val).count()
        if count > 0:
            sport_breakdown.append({'label': sport_label, 'count': count})

    return render(request, 'portal/cm/dashboard.html', {
        'stats': stats,
        'active_competitions': active,
        'registration_competitions': registration,
        'recent_results': recent_results,
        'pending_reports': pending_reports,
        'sport_breakdown': sport_breakdown,
    })


@role_required('competition_manager', 'admin')
def cm_create_competition_view(request):
    """Create a new competition."""
    from competitions.models import (
        Competition, SportType, GenderChoice, CompetitionFormat,
        AgeGroup, CompetitionStatus,
    )

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        sport_type = request.POST.get('sport_type', SportType.FOOTBALL_MEN)
        gender = request.POST.get('gender', GenderChoice.MEN)
        format_type = request.POST.get('format_type', CompetitionFormat.GROUP_AND_KNOCKOUT)
        season = request.POST.get('season', '2025')
        age_group = request.POST.get('age_group', AgeGroup.U17)
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        max_teams = request.POST.get('max_teams', 16)
        teams_per_group = request.POST.get('teams_per_group', 4)
        qualify_from_group = request.POST.get('qualify_from_group', 2)
        description = request.POST.get('description', '')
        rules = request.POST.get('rules', '')

        if not name or not start_date or not end_date:
            messages.error(request, 'Name, start date, and end date are required.')
        elif Competition.objects.filter(name=name).exists():
            messages.error(request, f'A competition named "{name}" already exists.')
        else:
            comp = Competition.objects.create(
                name=name,
                sport_type=sport_type,
                gender=gender,
                format_type=format_type,
                season=season,
                age_group=age_group,
                status=CompetitionStatus.REGISTRATION,
                start_date=start_date,
                end_date=end_date,
                max_teams=int(max_teams),
                teams_per_group=int(teams_per_group),
                qualify_from_group=int(qualify_from_group),
                description=description,
                rules=rules,
                created_by=request.user,
            )
            # Audit log
            from admin_dashboard.models import ActivityLog
            ActivityLog.objects.create(
                user=request.user,
                action='COMPETITION_CREATED',
                description=f'{request.user.get_full_name()} created competition: {comp.name}',
                object_repr=str(comp),
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            messages.success(request, f'Competition "{comp.name}" created successfully.')
            return redirect('cm_competition_manage', pk=comp.pk)

    return render(request, 'portal/cm/create_competition.html', {
        'sport_types': SportType.choices,
        'gender_choices': GenderChoice.choices,
        'format_choices': CompetitionFormat.choices,
        'age_groups': AgeGroup.choices,
    })


@role_required('competition_manager', 'admin')
def cm_edit_competition_view(request, pk):
    """Edit an existing competition."""
    from competitions.models import (
        Competition, SportType, GenderChoice, CompetitionFormat,
        AgeGroup, CompetitionStatus,
    )
    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        competition.name = request.POST.get('name', competition.name).strip()
        competition.sport_type = request.POST.get('sport_type', competition.sport_type)
        competition.gender = request.POST.get('gender', competition.gender)
        competition.format_type = request.POST.get('format_type', competition.format_type)
        competition.season = request.POST.get('season', competition.season)
        competition.age_group = request.POST.get('age_group', competition.age_group)
        competition.status = request.POST.get('status', competition.status)
        competition.start_date = request.POST.get('start_date', competition.start_date)
        competition.end_date = request.POST.get('end_date', competition.end_date)
        competition.max_teams = int(request.POST.get('max_teams', competition.max_teams))
        competition.teams_per_group = int(request.POST.get('teams_per_group', competition.teams_per_group))
        competition.qualify_from_group = int(request.POST.get('qualify_from_group', competition.qualify_from_group))
        competition.description = request.POST.get('description', competition.description)
        competition.rules = request.POST.get('rules', competition.rules)
        competition.save()

        messages.success(request, f'Competition "{competition.name}" updated.')
        return redirect('cm_competition_manage', pk=competition.pk)

    return render(request, 'portal/cm/edit_competition.html', {
        'competition': competition,
        'sport_types': SportType.choices,
        'gender_choices': GenderChoice.choices,
        'format_choices': CompetitionFormat.choices,
        'age_groups': AgeGroup.choices,
        'status_choices': CompetitionStatus.choices,
    })


@role_required('competition_manager', 'admin')
def cm_competition_manage_view(request, pk):
    """
    Central management hub for a competition.
    Shows pools, teams, fixtures, standings at a glance.
    """
    from competitions.models import (
        Competition, Pool, PoolTeam, Fixture, Venue, KnockoutRound,
        CountyPayment,
    )
    from matches.models import MatchReport

    competition = get_object_or_404(Competition, pk=pk)

    # Pools & teams
    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team'
    ).order_by('name')

    pool_data = []
    for pool in pools:
        teams = pool.pool_teams.select_related('team').all()
        sorted_teams = sorted(
            teams,
            key=lambda pt: (pt.points, pt.goal_difference, pt.goals_for),
            reverse=True
        )
        pool_data.append({'pool': pool, 'teams': sorted_teams})

    # Registered teams eligible for this competition (paid county, approved)
    eligible_teams = Team.objects.filter(
        status='registered',
        payment_confirmed=True,
        sport_type=competition.sport_type,
    ).exclude(
        pk__in=PoolTeam.objects.filter(
            pool__competition=competition
        ).values_list('team_id', flat=True)
    ).order_by('county', 'name')

    # All teams already in this competition
    teams_in_comp = Team.objects.filter(
        pool_memberships__pool__competition=competition
    ).distinct()

    # Fixtures
    group_fixtures = Fixture.objects.filter(
        competition=competition, is_knockout=False
    ).select_related('home_team', 'away_team', 'venue', 'pool').order_by('match_date', 'kickoff_time')

    knockout_fixtures = Fixture.objects.filter(
        competition=competition, is_knockout=True
    ).select_related('home_team', 'away_team', 'venue', 'winner').order_by(
        'knockout_round', 'bracket_position'
    )

    # Venues
    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')

    # Match reports
    pending_reports = MatchReport.objects.filter(
        fixture__competition=competition, status='submitted'
    ).count()
    approved_reports = MatchReport.objects.filter(
        fixture__competition=competition, status='approved'
    ).count()

    return render(request, 'portal/cm/manage_competition.html', {
        'competition': competition,
        'pool_data': pool_data,
        'eligible_teams': eligible_teams,
        'teams_in_comp': teams_in_comp,
        'group_fixtures': group_fixtures,
        'knockout_fixtures': knockout_fixtures,
        'venues': venues,
        'pending_reports': pending_reports,
        'approved_reports': approved_reports,
    })


@role_required('competition_manager', 'admin')
def cm_manage_pools_view(request, pk):
    """Create/delete pools and assign/remove teams."""
    from competitions.models import Competition, Pool, PoolTeam, CountyPayment

    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create_pool':
            pool_name = request.POST.get('pool_name', '').strip()
            if not pool_name:
                messages.error(request, 'Pool name is required.')
            elif Pool.objects.filter(competition=competition, name=pool_name).exists():
                messages.error(request, f'Pool "{pool_name}" already exists.')
            else:
                Pool.objects.create(competition=competition, name=pool_name)
                messages.success(request, f'Pool "{pool_name}" created.')

        elif action == 'delete_pool':
            pool_id = request.POST.get('pool_id')
            try:
                pool = Pool.objects.get(pk=pool_id, competition=competition)
                name = pool.name
                pool.delete()
                messages.success(request, f'Pool "{name}" deleted.')
            except Pool.DoesNotExist:
                messages.error(request, 'Pool not found.')

        elif action == 'add_team':
            pool_id = request.POST.get('pool_id')
            team_id = request.POST.get('team_id')
            try:
                pool = Pool.objects.get(pk=pool_id, competition=competition)
                team = Team.objects.get(pk=team_id)

                # Validate payment
                if not team.payment_confirmed:
                    messages.error(request, f'{team.name} cannot be pooled — payment not confirmed.')
                elif team.status != 'registered':
                    messages.error(request, f'{team.name} is not approved.')
                elif PoolTeam.objects.filter(pool__competition=competition, team=team).exists():
                    messages.error(request, f'{team.name} is already in a pool for this competition.')
                else:
                    PoolTeam.objects.create(pool=pool, team=team)
                    messages.success(request, f'{team.name} added to {pool.name}.')
            except (Pool.DoesNotExist, Team.DoesNotExist):
                messages.error(request, 'Pool or team not found.')

        elif action == 'remove_team':
            pt_id = request.POST.get('pool_team_id')
            try:
                pt = PoolTeam.objects.get(pk=pt_id, pool__competition=competition)
                name = pt.team.name
                pool_name = pt.pool.name
                pt.delete()
                messages.success(request, f'{name} removed from {pool_name}.')
            except PoolTeam.DoesNotExist:
                messages.error(request, 'Team assignment not found.')

        return redirect('cm_manage_pools', pk=competition.pk)

    # GET
    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team'
    ).order_by('name')

    # Eligible teams not yet in any pool for this competition
    assigned_ids = PoolTeam.objects.filter(
        pool__competition=competition
    ).values_list('team_id', flat=True)

    eligible_teams = Team.objects.filter(
        status='registered',
        payment_confirmed=True,
        sport_type=competition.sport_type,
    ).exclude(pk__in=assigned_ids).order_by('county', 'name')

    return render(request, 'portal/cm/manage_pools.html', {
        'competition': competition,
        'pools': pools,
        'eligible_teams': eligible_teams,
    })


@role_required('competition_manager', 'admin')
def cm_generate_fixtures_view(request, pk):
    """Generate fixtures for a competition."""
    from competitions.models import Competition, Fixture, Venue, Pool
    from competitions.fixture_engine import generate_all_fixtures

    competition = get_object_or_404(Competition, pk=pk)

    # Check if fixtures already exist
    existing_count = Fixture.objects.filter(competition=competition).count()

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'generate':
            start_date_str = request.POST.get('start_date', '')
            kickoff_time_str = request.POST.get('kickoff_time', '14:00')
            group_interval = int(request.POST.get('group_interval', 7))
            knockout_interval = int(request.POST.get('knockout_interval', 3))
            venue_id = request.POST.get('venue_id', '')
            knockout_teams = request.POST.get('knockout_teams', '')

            from datetime import datetime
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                messages.error(request, 'Invalid start date.')
                return redirect('cm_generate_fixtures', pk=pk)

            try:
                kickoff_time = datetime.strptime(kickoff_time_str, '%H:%M').time()
            except (ValueError, TypeError):
                kickoff_time = datetime.strptime('14:00', '%H:%M').time()

            venue = None
            if venue_id:
                try:
                    venue = Venue.objects.get(pk=venue_id)
                except Venue.DoesNotExist:
                    pass

            ko_teams = int(knockout_teams) if knockout_teams else None

            try:
                fixtures = generate_all_fixtures(
                    competition, start_date, kickoff_time,
                    group_interval=group_interval,
                    knockout_interval=knockout_interval,
                    knockout_teams=ko_teams,
                    venue=venue,
                    created_by=request.user,
                )

                from admin_dashboard.models import ActivityLog
                ActivityLog.objects.create(
                    user=request.user,
                    action='FIXTURES_GENERATED',
                    description=(
                        f'{request.user.get_full_name()} generated {len(fixtures)} '
                        f'fixtures for {competition.name}'
                    ),
                    object_repr=str(competition),
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )

                messages.success(
                    request,
                    f'{len(fixtures)} fixtures generated for {competition.name}.'
                )
            except ValueError as e:
                messages.error(request, str(e))

            return redirect('cm_competition_manage', pk=pk)

        elif action == 'clear':
            count = Fixture.objects.filter(competition=competition).count()
            Fixture.objects.filter(competition=competition).delete()
            messages.warning(request, f'{count} fixtures deleted.')
            return redirect('cm_generate_fixtures', pk=pk)

    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')
    pools = Pool.objects.filter(competition=competition).prefetch_related('pool_teams')
    total_pool_teams = sum(p.pool_teams.count() for p in pools)

    return render(request, 'portal/cm/generate_fixtures.html', {
        'competition': competition,
        'existing_count': existing_count,
        'venues': venues,
        'pools': pools,
        'total_pool_teams': total_pool_teams,
    })


@role_required('competition_manager', 'admin')
def cm_manage_venues_view(request):
    """Manage venues — list, create, edit."""
    from competitions.models import Venue

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'create':
            name = request.POST.get('name', '').strip()
            county = request.POST.get('county', '').strip()
            city = request.POST.get('city', '').strip()
            capacity = request.POST.get('capacity', 0)
            surface = request.POST.get('surface', 'Natural Grass')
            address = request.POST.get('address', '')
            facilities = request.POST.get('facilities', '')

            if not name or not county:
                messages.error(request, 'Venue name and county are required.')
            else:
                Venue.objects.create(
                    name=name, county=county, city=city,
                    capacity=int(capacity) if capacity else 0,
                    surface=surface, address=address, facilities=facilities,
                )
                messages.success(request, f'Venue "{name}" created.')

        elif action == 'toggle':
            venue_id = request.POST.get('venue_id')
            try:
                venue = Venue.objects.get(pk=venue_id)
                venue.is_active = not venue.is_active
                venue.save(update_fields=['is_active'])
                status = 'activated' if venue.is_active else 'deactivated'
                messages.success(request, f'Venue "{venue.name}" {status}.')
            except Venue.DoesNotExist:
                messages.error(request, 'Venue not found.')

        elif action == 'update':
            venue_id = request.POST.get('venue_id')
            try:
                venue = Venue.objects.get(pk=venue_id)
                venue.name = request.POST.get('name', venue.name).strip()
                venue.county = request.POST.get('county', venue.county).strip()
                venue.city = request.POST.get('city', venue.city).strip()
                venue.capacity = int(request.POST.get('capacity', venue.capacity) or 0)
                venue.surface = request.POST.get('surface', venue.surface)
                venue.address = request.POST.get('address', venue.address)
                venue.facilities = request.POST.get('facilities', venue.facilities)
                venue.save()
                messages.success(request, f'Venue "{venue.name}" updated.')
            except Venue.DoesNotExist:
                messages.error(request, 'Venue not found.')

        return redirect('cm_venues')

    venues = Venue.objects.all().order_by('county', 'name')
    active_venues = venues.filter(is_active=True)
    inactive_venues = venues.filter(is_active=False)

    return render(request, 'portal/cm/venues.html', {
        'active_venues': active_venues,
        'inactive_venues': inactive_venues,
        'total_venues': venues.count(),
        'county_choices': KenyaCounty.choices,
    })


@role_required('competition_manager', 'admin')
def cm_allocate_venue_view(request, pk):
    """Allocate venues to fixtures for a competition."""
    from competitions.models import Competition, Fixture, Venue

    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        # Bulk update venue assignments
        fixtures = Fixture.objects.filter(competition=competition)
        updated = 0
        for fixture in fixtures:
            venue_id = request.POST.get(f'venue_{fixture.pk}', '')
            if venue_id:
                try:
                    venue = Venue.objects.get(pk=venue_id)
                    if fixture.venue != venue:
                        fixture.venue = venue
                        fixture.save(update_fields=['venue'])
                        updated += 1
                except Venue.DoesNotExist:
                    pass
            elif fixture.venue:
                fixture.venue = None
                fixture.save(update_fields=['venue'])
                updated += 1

        messages.success(request, f'{updated} fixture venue(s) updated.')
        return redirect('cm_competition_manage', pk=pk)

    fixtures = Fixture.objects.filter(
        competition=competition
    ).select_related(
        'home_team', 'away_team', 'venue', 'pool'
    ).order_by('match_date', 'kickoff_time')

    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')

    return render(request, 'portal/cm/allocate_venues.html', {
        'competition': competition,
        'fixtures': fixtures,
        'venues': venues,
    })


@role_required('competition_manager', 'admin')
def cm_edit_standings_view(request, pk):
    """Admin override — manually edit pool team standings."""
    from competitions.models import Competition, Pool, PoolTeam

    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_standings':
            pool_team_id = request.POST.get('pool_team_id')
            try:
                pt = PoolTeam.objects.get(pk=pool_team_id, pool__competition=competition)
                pt.played = int(request.POST.get('played', pt.played))
                pt.won = int(request.POST.get('won', pt.won))
                pt.drawn = int(request.POST.get('drawn', pt.drawn))
                pt.lost = int(request.POST.get('lost', pt.lost))
                pt.goals_for = int(request.POST.get('goals_for', pt.goals_for))
                pt.goals_against = int(request.POST.get('goals_against', pt.goals_against))
                pt.bonus_points = int(request.POST.get('bonus_points', pt.bonus_points))
                pt.save()

                from admin_dashboard.models import ActivityLog
                ActivityLog.objects.create(
                    user=request.user,
                    action='STANDINGS_OVERRIDE',
                    description=(
                        f'{request.user.get_full_name()} manually edited standings for '
                        f'{pt.team.name} in {pt.pool.name} ({competition.name})'
                    ),
                    object_repr=str(pt),
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                )
                messages.success(request, f'Standings updated for {pt.team.name}.')
            except PoolTeam.DoesNotExist:
                messages.error(request, 'Pool team not found.')

        elif action == 'recalculate':
            pool_id = request.POST.get('pool_id')
            try:
                pool = Pool.objects.get(pk=pool_id, competition=competition)
                from matches.stats_engine import recalculate_pool_standings
                recalculate_pool_standings(pool)
                messages.success(request, f'Standings recalculated for {pool.name}.')
            except Pool.DoesNotExist:
                messages.error(request, 'Pool not found.')

        elif action == 'recalculate_all':
            pools = Pool.objects.filter(competition=competition)
            from matches.stats_engine import recalculate_pool_standings
            for pool in pools:
                recalculate_pool_standings(pool)
            messages.success(request, f'All pool standings recalculated for {competition.name}.')

        return redirect('cm_edit_standings', pk=pk)

    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team'
    ).order_by('name')

    pool_data = []
    for pool in pools:
        teams = pool.pool_teams.select_related('team').all()
        sorted_teams = sorted(
            teams,
            key=lambda pt: (pt.points, pt.goal_difference, pt.goals_for),
            reverse=True
        )
        pool_data.append({'pool': pool, 'teams': sorted_teams})

    return render(request, 'portal/cm/edit_standings.html', {
        'competition': competition,
        'pool_data': pool_data,
    })


@role_required('competition_manager', 'admin')
def cm_edit_fixture_view(request, pk, fixture_pk):
    """Edit a specific fixture (date, time, venue, teams for knockout)."""
    from competitions.models import Competition, Fixture, Venue

    competition = get_object_or_404(Competition, pk=pk)
    fixture = get_object_or_404(Fixture, pk=fixture_pk, competition=competition)

    if request.method == 'POST':
        fixture.match_date = request.POST.get('match_date', fixture.match_date)
        kickoff = request.POST.get('kickoff_time', '')
        if kickoff:
            from datetime import datetime
            try:
                fixture.kickoff_time = datetime.strptime(kickoff, '%H:%M').time()
            except ValueError:
                pass
        venue_id = request.POST.get('venue_id', '')
        if venue_id:
            try:
                fixture.venue = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                pass
        else:
            fixture.venue = None

        status = request.POST.get('status', fixture.status)
        if status:
            fixture.status = status

        # For knockout matches, allow team reassignment
        if fixture.is_knockout:
            home_id = request.POST.get('home_team_id', '')
            away_id = request.POST.get('away_team_id', '')
            if home_id:
                try:
                    fixture.home_team = Team.objects.get(pk=home_id)
                except Team.DoesNotExist:
                    pass
            if away_id:
                try:
                    fixture.away_team = Team.objects.get(pk=away_id)
                except Team.DoesNotExist:
                    pass

        fixture.save()
        messages.success(request, f'Fixture updated: {fixture}')
        return redirect('cm_competition_manage', pk=pk)

    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')
    from competitions.models import FixtureStatus
    teams = Team.objects.filter(
        status='registered', payment_confirmed=True
    ).order_by('name')

    return render(request, 'portal/cm/edit_fixture.html', {
        'competition': competition,
        'fixture': fixture,
        'venues': venues,
        'teams': teams,
        'status_choices': FixtureStatus.choices,
    })


@role_required('competition_manager', 'admin')
def cm_competition_rules_view(request, pk):
    """Edit and publish competition rules."""
    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        competition.rules = request.POST.get('rules', '')
        competition.save(update_fields=['rules'])
        messages.success(request, f'Rules updated for {competition.name}.')
        return redirect('cm_competition_manage', pk=pk)

    return render(request, 'portal/cm/edit_rules.html', {
        'competition': competition,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS DIRECTOR — PUBLIC REGISTRATION
# ══════════════════════════════════════════════════════════════════════════════

def county_admin_register_view(request):
    """Public county registration for KYISA 11th Edition."""
    # Build list of already-taken counties for the template
    taken_counties = list(
        CountyRegistration.objects.values_list('county', flat=True)
    )

    if request.method == 'POST':
        form = CountyAdminRegistrationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Auto-generate a secure temporary password
            temp_password = ''.join(
                secrets.choice(string.ascii_letters + string.digits)
                for _ in range(12)
            )
            user = User.objects.create_user(
                email=cd['email'],
                password=temp_password,
                first_name=cd['first_name'],
                last_name=cd['last_name'],
                phone=cd['phone'],
                county=cd['county'],
                role=UserRole.COUNTY_SPORTS_DIRECTOR,
            )
            user.must_change_password = True
            user.save(update_fields=['must_change_password'])

            CountyRegistration.objects.create(
                user=user,
                county=cd['county'],
                director_name=cd['director_name'],
                director_phone=cd['director_phone'],
            )
            messages.success(request, mark_safe(
                f'<strong>County Registration Successful!</strong><br>'
                f'County: <strong>{cd["county"]}</strong><br>'
                f'Director of Sports: <strong>{cd["director_name"]}</strong><br><br>'
                f'Your temporary password is: <code>{temp_password}</code><br>'
                f'<strong>Please save this password.</strong> You will be required to change it on first login.<br><br>'
                f'<strong>Next steps:</strong><br>'
                f'1. Log in to the portal with your email and the temporary password above<br>'
                f'2. Change your password when prompted<br>'
                f'3. Submit payment (M-Pesa or bank slip)<br>'
                f'4. Once the treasurer approves, you can add disciplines and players'
            ))
            return redirect('county_admin_register_success')
    else:
        form = CountyAdminRegistrationForm()

    return render(request, 'public/county_admin_register.html', {
        'form': form,
        'taken_counties': taken_counties,
        'active_page': 'register',
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


def county_admin_register_success_view(request):
    return render(request, 'public/county_admin_register_success.html', {
        'active_page': 'register',
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS ADMIN — PORTAL DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_dashboard_view(request):
    """County admin home — registration status, payment, disciplines, players."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    disciplines = reg.disciplines.all()
    player_count = sum(d.player_count for d in disciplines)

    return render(request, 'portal/county_admin/dashboard.html', {
        'reg': reg,
        'disciplines': disciplines,
        'player_count': player_count,
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS ADMIN — PAYMENT SUBMISSION
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_payment_view(request):
    """County admin submits payment proof (M-Pesa or bank slip)."""
    reg = get_object_or_404(CountyRegistration, user=request.user)

    if reg.status not in (CountyRegStatus.PENDING_PAYMENT, CountyRegStatus.REJECTED):
        messages.info(request, 'Payment has already been submitted.')
        return redirect('county_admin_dashboard')

    if request.method == 'POST':
        form = CountyPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            reg.mpesa_reference = cd.get('mpesa_reference', '')
            if cd.get('bank_slip'):
                reg.bank_slip = cd['bank_slip']
            reg.payment_amount = cd['payment_amount']
            reg.payment_submitted_at = timezone.now()
            reg.status = CountyRegStatus.PAYMENT_SUBMITTED
            reg.save()
            messages.success(request, 'Payment proof submitted! The treasurer will review it shortly.')
            return redirect('county_admin_dashboard')
    else:
        form = CountyPaymentForm()

    return render(request, 'portal/county_admin/payment.html', {
        'form': form,
        'reg': reg,
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS ADMIN — DISCIPLINE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_add_discipline_view(request):
    """County admin chooses which disciplines to participate in."""
    reg = get_object_or_404(CountyRegistration, user=request.user)

    if not reg.is_approved:
        messages.warning(request, 'You must be approved before adding disciplines.')
        return redirect('county_admin_dashboard')

    existing = set(reg.disciplines.values_list('sport_type', flat=True))
    available = [(k, v) for k, v in SQUAD_LIMITS.items() if k not in existing]

    if request.method == 'POST':
        sport = request.POST.get('sport_type', '')
        if sport in dict(SQUAD_LIMITS) and sport not in existing:
            CountyDiscipline.objects.create(registration=reg, sport_type=sport)
            messages.success(request, f'{dict(SportType.choices).get(sport, sport)} added.')
        else:
            messages.error(request, 'Invalid discipline or already added.')
        return redirect('county_admin_dashboard')

    return render(request, 'portal/county_admin/add_discipline.html', {
        'reg': reg,
        'available': [(k, dict(SportType.choices).get(k, k), v) for k, v in available],
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS ADMIN — PLAYER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_discipline_players_view(request, discipline_pk):
    """View players in a discipline and add new ones."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    discipline = get_object_or_404(CountyDiscipline, pk=discipline_pk, registration=reg)
    players = discipline.players.all()

    return render(request, 'portal/county_admin/discipline_players.html', {
        'reg': reg,
        'discipline': discipline,
        'players': players,
    })


@role_required('county_sports_admin')
def county_admin_add_player_view(request, discipline_pk):
    """Add a player to a discipline."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    discipline = get_object_or_404(CountyDiscipline, pk=discipline_pk, registration=reg)

    if not reg.is_approved:
        messages.warning(request, 'Registration must be approved before adding players.')
        return redirect('county_admin_dashboard')

    if not discipline.can_add_player:
        messages.error(
            request,
            f'Squad limit reached ({discipline.squad_limit}) for '
            f'{discipline.get_sport_type_display()}.'
        )
        return redirect('county_admin_discipline_players', discipline_pk=discipline_pk)

    if request.method == 'POST':
        form = CountyPlayerForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save(commit=False)
            player.discipline = discipline
            player.save()
            messages.success(
                request,
                f'{player.first_name} {player.last_name} registered '
                f'({discipline.player_count}/{discipline.squad_limit}).'
            )
            return redirect('county_admin_discipline_players', discipline_pk=discipline_pk)
    else:
        form = CountyPlayerForm()

    return render(request, 'portal/county_admin/add_player.html', {
        'form': form,
        'discipline': discipline,
        'reg': reg,
    })


@role_required('county_sports_admin')
def county_admin_delete_player_view(request, player_pk):
    """Remove a player from a discipline."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    player = get_object_or_404(CountyPlayer, pk=player_pk, discipline__registration=reg)
    discipline_pk = player.discipline.pk

    if request.method == 'POST':
        name = f'{player.first_name} {player.last_name}'
        player.delete()
        messages.success(request, f'{name} removed.')
    return redirect('county_admin_discipline_players', discipline_pk=discipline_pk)


# ══════════════════════════════════════════════════════════════════════════════
#   TREASURER — COUNTY REGISTRATION APPROVALS
# ══════════════════════════════════════════════════════════════════════════════

@role_required('treasurer', 'admin')
def treasurer_county_registrations_view(request):
    """Treasurer reviews county admin registrations and approves/rejects."""
    if request.method == 'POST':
        reg_id = request.POST.get('registration_id')
        action = request.POST.get('action')
        reg = get_object_or_404(CountyRegistration, pk=reg_id)

        if action == 'approve':
            reg.status = CountyRegStatus.APPROVED
            reg.approved_by = request.user
            reg.approved_at = timezone.now()
            reg.save()
            messages.success(request, f'{reg.county} county registration approved.')
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            reg.status = CountyRegStatus.REJECTED
            reg.rejection_reason = reason
            reg.save()
            messages.warning(request, f'{reg.county} county registration rejected.')

        return redirect('treasurer_county_registrations')

    pending = CountyRegistration.objects.filter(
        status=CountyRegStatus.PAYMENT_SUBMITTED
    ).order_by('-payment_submitted_at')
    approved = CountyRegistration.objects.filter(
        status=CountyRegStatus.APPROVED
    ).order_by('-approved_at')
    all_regs = CountyRegistration.objects.all().order_by('-created_at')

    return render(request, 'portal/treasurer/county_registrations.html', {
        'pending': pending,
        'approved': approved,
        'all_regs': all_regs,
        'registration_fee': COUNTY_REGISTRATION_FEE_CAP,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS DIRECTOR — TECHNICAL BENCH MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_add_bench_member_view(request, discipline_pk):
    """County sports director adds a technical bench member to a discipline."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    discipline = get_object_or_404(CountyDiscipline, pk=discipline_pk, registration=reg)

    if not reg.is_approved:
        messages.warning(request, 'Registration must be approved first.')
        return redirect('county_admin_dashboard')

    if request.method == 'POST':
        form = TechnicalBenchForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save(commit=False)
            member.discipline = discipline

            # Check if role is already filled
            if TechnicalBenchMember.objects.filter(discipline=discipline, role=member.role).exists():
                messages.error(request, f'{member.get_role_display()} is already assigned for this discipline.')
            else:
                member.save()

                # If this is a Team Manager, create a user account for them
                if member.role == TechnicalBenchRole.TEAM_MANAGER and member.email:
                    try:
                        import secrets, string
                        temp_pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
                        tm_user = User.objects.create_user(
                            email=member.email,
                            password=temp_pw,
                            first_name=member.first_name,
                            last_name=member.last_name,
                            phone=member.phone,
                            county=reg.county,
                            role=UserRole.TEAM_MANAGER,
                            must_change_password=True,
                        )
                        member.user = tm_user
                        member.save(update_fields=['user'])
                        messages.success(request, mark_safe(
                            f'<strong>{member.get_full_name}</strong> added as {member.get_role_display()}.<br>'
                            f'Login: <code>{member.email}</code><br>'
                            f'Temp password: <code>{temp_pw}</code><br>'
                            f'<em>They must change password on first login.</em>'
                        ))
                    except Exception as e:
                        member.save()
                        messages.warning(request, f'{member.get_full_name} added but account creation failed: {e}')
                else:
                    messages.success(request, f'{member.get_full_name} added as {member.get_role_display()}.')

            return redirect('county_admin_discipline_players', discipline_pk=discipline_pk)
    else:
        form = TechnicalBenchForm()

    existing_bench = discipline.technical_bench.all()
    filled_roles = set(existing_bench.values_list('role', flat=True))
    available_roles = [(k, v) for k, v in TechnicalBenchRole.choices if k not in filled_roles]

    return render(request, 'portal/county_admin/add_bench_member.html', {
        'form': form,
        'discipline': discipline,
        'reg': reg,
        'existing_bench': existing_bench,
        'available_roles': available_roles,
    })


@role_required('county_sports_admin')
def county_admin_delete_bench_member_view(request, member_pk):
    """Remove a technical bench member."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    member = get_object_or_404(TechnicalBenchMember, pk=member_pk, discipline__registration=reg)
    discipline_pk = member.discipline.pk

    if request.method == 'POST':
        name = member.get_full_name
        member.delete()
        messages.success(request, f'{name} removed from technical bench.')
    return redirect('county_admin_discipline_players', discipline_pk=discipline_pk)


# ══════════════════════════════════════════════════════════════════════════════
#   COUNTY SPORTS DIRECTOR — PLAYER VERIFICATION OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

@role_required('county_sports_admin')
def county_admin_verification_view(request):
    """County sports director views verification status of all their players."""
    reg = get_object_or_404(CountyRegistration, user=request.user)
    disciplines = reg.disciplines.prefetch_related('players').all()

    approved_players = []
    rejected_players = []
    resubmit_players = []
    pending_players = []

    for disc in disciplines:
        for player in disc.players.all():
            entry = {'player': player, 'discipline': disc}
            if player.verification_status == 'verified':
                approved_players.append(entry)
            elif player.verification_status == 'rejected':
                rejected_players.append(entry)
            elif player.verification_status == 'resubmit':
                resubmit_players.append(entry)
            else:
                pending_players.append(entry)

    return render(request, 'portal/county_admin/verification_status.html', {
        'reg': reg,
        'approved_players': approved_players,
        'rejected_players': rejected_players,
        'resubmit_players': resubmit_players,
        'pending_players': pending_players,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   PLAYER PROFILE VIEW (public within portal)
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='web_login')
def player_profile_view(request, player_pk):
    """
    Player profile view showing full details, verification status,
    discipline(s), and passport photo. Accessible to authorized roles.
    """
    # Try CountyPlayer first, then Player (team-based)
    player = None
    player_type = None
    try:
        player = CountyPlayer.objects.select_related('discipline__registration').get(pk=player_pk)
        player_type = 'county'
    except CountyPlayer.DoesNotExist:
        pass

    if not player:
        player = get_object_or_404(Player.objects.select_related('team'), pk=player_pk)
        player_type = 'team'

    # Access control
    user = request.user
    can_view = (
        user.is_superuser or
        user.role in ('admin', 'competition_manager', 'referee', 'referee_manager', 'jury_chair')
    )
    if player_type == 'county':
        # County sports director can view their own county's players
        if user.role == 'county_sports_admin':
            try:
                reg = CountyRegistration.objects.get(user=user)
                if player.discipline.registration == reg:
                    can_view = True
            except CountyRegistration.DoesNotExist:
                pass
        # Team manager can view verified players in their county
        if user.role == 'team_manager':
            try:
                bench = TechnicalBenchMember.objects.get(user=user)
                if bench.discipline.registration == player.discipline.registration:
                    can_view = True
            except TechnicalBenchMember.DoesNotExist:
                pass
    elif player_type == 'team':
        if user.role == 'team_manager' and player.team.manager == user:
            can_view = True

    if not can_view:
        messages.error(request, 'You do not have permission to view this player profile.')
        return redirect('dashboard')

    return render(request, 'portal/player_profile.html', {
        'player': player,
        'player_type': player_type,
    })


@login_required(login_url='web_login')
def county_player_profile_view(request, player_pk):
    """County player profile view — redirect to the unified player profile."""
    return player_profile_view(request, player_pk)


# ══════════════════════════════════════════════════════════════════════════════
#   TEAM MANAGER PORTAL (dedicated portal for match management)
# ══════════════════════════════════════════════════════════════════════════════

@role_required('team_manager')
def team_manager_dashboard_view(request):
    """
    Team Manager dedicated dashboard showing:
    - Verified players (organized per discipline)
    - Upcoming matches
    - Disciplinary sanctions for own + opponent teams
    """
    user = request.user

    # Find the technical bench member linked to this user
    try:
        bench = TechnicalBenchMember.objects.select_related(
            'discipline__registration'
        ).get(user=user, role=TechnicalBenchRole.TEAM_MANAGER)
    except TechnicalBenchMember.DoesNotExist:
        bench = None

    # Fall back to old Team-based manager role
    my_teams = Team.objects.filter(manager=user)

    # Verified county players (if bench member)
    verified_players = []
    discipline = None
    county_reg = None
    if bench:
        discipline = bench.discipline
        county_reg = discipline.registration
        verified_players = CountyPlayer.objects.filter(
            discipline=discipline,
            verification_status='verified',
        ).order_by('last_name', 'first_name')

    # Verified team players (old flow)
    team_players = {}
    for team in my_teams:
        team_players[team] = Player.objects.filter(
            team=team,
            verification_status=VerificationStatus.VERIFIED,
            huduma_status='verified',
            fifa_connect_status='clear',
        ).order_by('shirt_number')

    # Upcoming fixtures
    upcoming_fixtures = []
    if my_teams.exists():
        upcoming_fixtures = Fixture.objects.filter(
            Q(home_team__in=my_teams) | Q(away_team__in=my_teams),
            match_date__gte=timezone.now(),
        ).select_related(
            'competition', 'home_team', 'away_team', 'venue'
        ).order_by('match_date')[:10]

    # Disciplinary sanctions
    from matches.models import PlayerStatistics
    own_sanctions = []
    opponent_sanctions = []
    if my_teams.exists():
        own_sanctions = PlayerStatistics.objects.filter(
            team__in=my_teams,
        ).filter(
            Q(yellow_cards__gt=0) | Q(red_cards__gt=0)
        ).select_related('player', 'team', 'competition').order_by('-red_cards', '-yellow_cards')[:20]

    return render(request, 'portal/team_manager/dashboard.html', {
        'bench': bench,
        'discipline': discipline,
        'county_reg': county_reg,
        'verified_players': verified_players,
        'my_teams': my_teams,
        'team_players': team_players,
        'upcoming_fixtures': upcoming_fixtures,
        'own_sanctions': own_sanctions,
    })


@role_required('team_manager')
def team_manager_match_squad_view(request, fixture_pk):
    """
    Team Manager selects match day squad (starting 11 + subs).
    - Only verified players can be selected
    - Suspended players are blocked
    - Cannot edit after match start
    - Post-referee-approval edits require re-approval
    """
    from django.conf import settings as conf

    fixture = get_object_or_404(Fixture.objects.select_related(
        'home_team', 'away_team', 'competition', 'venue'
    ), pk=fixture_pk)
    user = request.user

    # Determine the manager's team
    my_teams = Team.objects.filter(manager=user)
    team = None
    if fixture.home_team in my_teams:
        team = fixture.home_team
    elif fixture.away_team in my_teams:
        team = fixture.away_team

    if not team:
        messages.error(request, 'Your team is not involved in this fixture.')
        return redirect('team_manager_dashboard')

    # Check match hasn't started
    if fixture.status in ('live', 'completed'):
        messages.error(request, 'Cannot edit squad — match has already started or completed.')
        return redirect('team_manager_dashboard')

    # Get existing submission
    existing = SquadSubmission.objects.filter(fixture=fixture, team=team).first()

    # If squad already approved by referee, warn that changes need re-approval
    needs_re_approval = existing and existing.status == SquadStatus.APPROVED

    # Get fully verified players only — suspended ones flagged
    eligible_players = Player.objects.filter(
        team=team,
        verification_status=VerificationStatus.VERIFIED,
        huduma_status='verified',
        fifa_connect_status='clear',
    ).order_by('shirt_number')

    suspended_ids = set(
        Player.objects.filter(
            team=team, status=PlayerStatus.SUSPENDED
        ).values_list('pk', flat=True)
    )

    starter_ids = []
    sub_ids = []
    if existing:
        starter_ids = list(existing.squad_players.filter(is_starter=True).values_list('player_id', flat=True))
        sub_ids = list(existing.squad_players.filter(is_starter=False).values_list('player_id', flat=True))

    if request.method == 'POST':
        selected_starters = request.POST.getlist('starters')
        selected_subs = request.POST.getlist('subs')

        starters_int = [int(x) for x in selected_starters if x]
        subs_int = [int(x) for x in selected_subs if x]

        # Validate no suspended players
        selected_suspended = (set(starters_int) | set(subs_int)) & suspended_ids
        if selected_suspended:
            messages.error(request, 'Cannot select suspended players.')
        elif set(starters_int) & set(subs_int):
            messages.error(request, 'A player cannot be both a starter and a substitute.')
        elif len(starters_int) != 11:
            messages.error(request, f'Exactly 11 starters required. You selected {len(starters_int)}.')
        else:
            if existing:
                existing.squad_players.all().delete()
                submission = existing
            else:
                submission = SquadSubmission.objects.create(fixture=fixture, team=team)

            # If was previously approved and now re-submitted, needs re-approval
            submission.status = SquadStatus.SUBMITTED
            submission.submitted_at = timezone.now()
            submission.rejection_reason = ''
            submission.reviewed_by = None
            submission.reviewed_at = None
            submission.save()

            for pid in starters_int:
                p = Player.objects.get(pk=pid, team=team)
                SquadPlayer.objects.create(submission=submission, player=p, is_starter=True, shirt_number=p.shirt_number)
            for pid in subs_int:
                p = Player.objects.get(pk=pid, team=team)
                SquadPlayer.objects.create(submission=submission, player=p, is_starter=False, shirt_number=p.shirt_number)

            messages.success(request, f'Squad submitted for {fixture}.')
            return redirect('team_manager_dashboard')

    return render(request, 'portal/team_manager/match_squad.html', {
        'fixture': fixture,
        'team': team,
        'eligible_players': eligible_players,
        'suspended_ids': suspended_ids,
        'existing': existing,
        'starter_ids': starter_ids,
        'sub_ids': sub_ids,
        'needs_re_approval': needs_re_approval,
    })


@role_required('team_manager')
def team_manager_opponent_view(request, fixture_pk):
    """
    View opponent team list — ONLY after referee has approved both squads.
    """
    fixture = get_object_or_404(Fixture.objects.select_related(
        'home_team', 'away_team', 'competition'
    ), pk=fixture_pk)
    user = request.user

    my_teams = Team.objects.filter(manager=user)
    if fixture.home_team in my_teams:
        my_team = fixture.home_team
        opponent = fixture.away_team
    elif fixture.away_team in my_teams:
        my_team = fixture.away_team
        opponent = fixture.home_team
    else:
        messages.error(request, 'Your team is not involved in this fixture.')
        return redirect('team_manager_dashboard')

    # Check both squads are approved
    my_squad = SquadSubmission.objects.filter(fixture=fixture, team=my_team).first()
    opp_squad = SquadSubmission.objects.filter(fixture=fixture, team=opponent).first()

    both_approved = (
        my_squad and my_squad.status == SquadStatus.APPROVED and
        opp_squad and opp_squad.status == SquadStatus.APPROVED
    )

    if not both_approved:
        messages.warning(request, 'Opponent team list is only visible after referee approves both squads.')
        return redirect('team_manager_dashboard')

    opp_players = opp_squad.squad_players.select_related('player').order_by('-is_starter', 'shirt_number')

    return render(request, 'portal/team_manager/opponent_view.html', {
        'fixture': fixture,
        'my_team': my_team,
        'opponent': opponent,
        'opp_players': opp_players,
    })


@role_required('team_manager')
def team_manager_sanctions_view(request):
    """View disciplinary sanctions for own team and opponents."""
    user = request.user
    my_teams = Team.objects.filter(manager=user)
    from matches.models import PlayerStatistics

    own_sanctions = PlayerStatistics.objects.filter(
        team__in=my_teams,
    ).filter(
        Q(yellow_cards__gt=0) | Q(red_cards__gt=0)
    ).select_related('player', 'team', 'competition').order_by('-red_cards', '-yellow_cards')

    # Opponent sanctions: get from recent fixtures
    opponent_team_ids = set()
    recent_fixtures = Fixture.objects.filter(
        Q(home_team__in=my_teams) | Q(away_team__in=my_teams),
    ).select_related('home_team', 'away_team')[:20]

    for f in recent_fixtures:
        if f.home_team in my_teams:
            opponent_team_ids.add(f.away_team_id)
        else:
            opponent_team_ids.add(f.home_team_id)

    opponent_sanctions = PlayerStatistics.objects.filter(
        team_id__in=opponent_team_ids,
    ).filter(
        Q(yellow_cards__gt=0) | Q(red_cards__gt=0)
    ).select_related('player', 'team', 'competition').order_by('-red_cards', '-yellow_cards')[:30]

    return render(request, 'portal/team_manager/sanctions.html', {
        'own_sanctions': own_sanctions,
        'opponent_sanctions': opponent_sanctions,
        'my_teams': my_teams,
    })


@role_required('team_manager')
def team_manager_file_appeal_view(request):
    """
    Team Manager files a disciplinary appeal.
    Appeals must be reviewed and approved by the County Sports Director before proceeding.
    """
    from appeals.forms import AppealForm
    user = request.user
    my_teams = Team.objects.filter(manager=user)

    if not my_teams.exists():
        messages.error(request, 'No team found for your account.')
        return redirect('team_manager_dashboard')

    team = my_teams.first()

    if request.method == 'POST':
        form = AppealForm(request.POST)
        if form.is_valid():
            from appeals.models import Appeal, AppealStatus
            respondent_team_id = request.POST.get('respondent_team')
            if not respondent_team_id:
                messages.error(request, 'Please select a respondent team.')
            else:
                appeal = Appeal(
                    appellant_team=team,
                    appellant_user=user,
                    respondent_team_id=int(respondent_team_id),
                    subject=form.cleaned_data['subject'],
                    details=form.cleaned_data['details'],
                    status=AppealStatus.DRAFT,
                )
                match_id = request.POST.get('match')
                if match_id:
                    appeal.match_id = int(match_id)
                appeal.save()
                messages.success(request, 'Appeal drafted. It will be reviewed by your County Sports Director before submission.')
                return redirect('team_manager_dashboard')
    else:
        form = AppealForm()

    # Get possible opponent teams
    other_teams = Team.objects.exclude(pk__in=my_teams).filter(status='registered').order_by('name')

    return render(request, 'portal/team_manager/file_appeal.html', {
        'form': form,
        'team': team,
        'other_teams': other_teams,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   TEAM LIST — DOWNLOADABLE PDF
# ══════════════════════════════════════════════════════════════════════════════

@login_required(login_url='web_login')
def team_list_pdf_view(request, discipline_pk):
    """
    Generate and return a downloadable PDF of the team list.
    Accessible to Team Manager and County Sports Director.
    """
    from django.http import HttpResponse
    from io import BytesIO

    discipline = get_object_or_404(
        CountyDiscipline.objects.select_related('registration'),
        pk=discipline_pk,
    )

    # Permission check
    user = request.user
    can_download = (
        user.is_superuser or
        user.role in ('admin', 'competition_manager')
    )
    if user.role == 'county_sports_admin':
        try:
            reg = CountyRegistration.objects.get(user=user)
            if discipline.registration == reg:
                can_download = True
        except CountyRegistration.DoesNotExist:
            pass
    if user.role == 'team_manager':
        try:
            bench = TechnicalBenchMember.objects.get(user=user)
            if bench.discipline == discipline:
                can_download = True
        except TechnicalBenchMember.DoesNotExist:
            pass

    if not can_download:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    players = discipline.players.filter(verification_status='verified').order_by('jersey_number', 'last_name')
    bench_members = discipline.technical_bench.all().order_by('role')

    # Generate PDF using reportlab
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm, mm

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Title'],
            fontSize=16, spaceAfter=6,
        )
        elements.append(Paragraph(
            f"{discipline.registration.county} County — {discipline.get_sport_type_display()}",
            title_style,
        ))
        elements.append(Paragraph("Official Team List", styles['Heading2']))
        elements.append(Spacer(1, 0.5*cm))

        # Technical bench section
        if bench_members.exists():
            elements.append(Paragraph("Technical Bench / Delegation", styles['Heading3']))
            bench_data = [['Role', 'Name', 'Phone']]
            for m in bench_members:
                bench_data.append([m.get_role_display(), m.get_full_name, m.phone])
            bench_table = Table(bench_data, colWidths=[5*cm, 7*cm, 5*cm])
            bench_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(bench_table)
            elements.append(Spacer(1, 0.5*cm))

        # Players section
        elements.append(Paragraph(f"Players ({players.count()})", styles['Heading3']))

        if players.exists():
            player_data = [['#', 'Name', 'Age', 'Position', 'Jersey']]
            for p in players:
                player_data.append([
                    str(players.filter(pk__lte=p.pk).count()),
                    p.get_full_name,
                    str(p.age),
                    p.position or '—',
                    str(p.jersey_number) if p.jersey_number else '—',
                ])

            player_table = Table(player_data, colWidths=[1.5*cm, 7*cm, 2*cm, 3*cm, 2.5*cm])
            player_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B5E20')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(player_table)
        else:
            elements.append(Paragraph("No verified players.", styles['Normal']))

        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph(
            f"Generated on {timezone.now().strftime('%d %B %Y at %H:%M')} — KYISA CMS",
            styles['Normal'],
        ))

        doc.build(elements)
        buffer.seek(0)

        county = discipline.registration.county
        sport = discipline.get_sport_type_display().replace(' ', '_')
        filename = f"KYISA_{county}_{sport}_Team_List.pdf"

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ImportError:
        messages.error(request, 'PDF generation requires the reportlab package. Install it with: pip install reportlab')
        return redirect('county_admin_dashboard')


# ══════════════════════════════════════════════════════════════════════════════
#   SECRETARY GENERAL — READ-ONLY OVERSIGHT PORTAL
# ══════════════════════════════════════════════════════════════════════════════

@role_required('secretary_general')
def sg_dashboard_view(request):
    """Secretary General overview: stats, recent actions, quick links."""
    from admin_dashboard.models import ActivityLog

    total_players = CountyPlayer.objects.count()
    verified_players = CountyPlayer.objects.filter(verification_status='verified').count()
    pending_players = CountyPlayer.objects.filter(verification_status='pending').count()
    rejected_players = CountyPlayer.objects.filter(verification_status='rejected').count()

    from appeals.models import Appeal, AppealStatus
    total_appeals = Appeal.objects.count()
    pending_appeals = Appeal.objects.filter(status=AppealStatus.SUBMITTED).count()
    decided_appeals = Appeal.objects.filter(status=AppealStatus.DECIDED).count()

    recent_activity = ActivityLog.objects.select_related('user').order_by('-timestamp')[:15]

    disciplines = CountyDiscipline.objects.select_related('registration').all()
    sport_breakdown = {}
    for d in disciplines:
        sport = d.get_sport_type_display()
        if sport not in sport_breakdown:
            sport_breakdown[sport] = {'total': 0, 'verified': 0}
        sport_breakdown[sport]['total'] += d.players.count()
        sport_breakdown[sport]['verified'] += d.players.filter(verification_status='verified').count()

    return render(request, 'portal/secretary_general/dashboard.html', {
        'total_players': total_players,
        'verified_players': verified_players,
        'pending_players': pending_players,
        'rejected_players': rejected_players,
        'total_appeals': total_appeals,
        'pending_appeals': pending_appeals,
        'decided_appeals': decided_appeals,
        'recent_activity': recent_activity,
        'sport_breakdown': sport_breakdown,
        'total_counties': CountyRegistration.objects.count(),
    })


@role_required('secretary_general')
def sg_verifications_view(request):
    """SG: View all player verifications across all disciplines (read-only)."""
    tab = request.GET.get('tab', 'verified')
    discipline_filter = request.GET.get('discipline', '')

    players = CountyPlayer.objects.select_related(
        'discipline', 'discipline__registration', 'verified_by',
    ).order_by('-verified_at', 'last_name')

    if discipline_filter:
        players = players.filter(discipline__sport_type=discipline_filter)

    verified = players.filter(verification_status='verified')
    pending = players.filter(verification_status='pending')
    rejected = players.filter(verification_status='rejected')

    disciplines = CountyDiscipline.objects.values_list(
        'sport_type', flat=True
    ).distinct()

    return render(request, 'portal/secretary_general/verifications.html', {
        'tab': tab,
        'verified_players': verified,
        'pending_players': pending,
        'rejected_players': rejected,
        'disciplines': disciplines,
        'discipline_filter': discipline_filter,
        'stats': {
            'verified': verified.count(),
            'pending': pending.count(),
            'rejected': rejected.count(),
        },
    })


@role_required('secretary_general')
def sg_appeals_view(request):
    """SG: View all appeals and their decisions (read-only)."""
    from appeals.models import Appeal, AppealStatus, JuryDecision

    status_filter = request.GET.get('status', '')
    appeals = Appeal.objects.select_related(
        'appellant_team', 'respondent_team', 'appellant_user', 'competition',
    ).order_by('-created_at')

    if status_filter:
        appeals = appeals.filter(status=status_filter)

    return render(request, 'portal/secretary_general/appeals.html', {
        'appeals': appeals,
        'status_choices': AppealStatus.choices,
        'current_status': status_filter,
    })


@role_required('secretary_general')
def sg_treasurer_actions_view(request):
    """SG: View all actions performed by the Treasurer."""
    from admin_dashboard.models import ActivityLog

    treasurer_logs = ActivityLog.objects.filter(
        user__role='treasurer',
    ).select_related('user').order_by('-timestamp')

    return render(request, 'portal/secretary_general/treasurer_actions.html', {
        'logs': treasurer_logs,
    })


@role_required('secretary_general')
def sg_user_actions_view(request):
    """SG: View all user activity — filterable by user and action type."""
    from admin_dashboard.models import ActivityLog

    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')

    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')

    if user_filter:
        logs = logs.filter(user_id=user_filter)
    if action_filter:
        logs = logs.filter(action=action_filter)

    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    action_choices = ActivityLog.ACTION_CHOICES

    return render(request, 'portal/secretary_general/user_actions.html', {
        'logs': logs[:200],
        'users': users,
        'action_choices': action_choices,
        'user_filter': user_filter,
        'action_filter': action_filter,
    })


@role_required('secretary_general')
def sg_verified_players_view(request):
    """SG: View verified players for all disciplines — who verified, when, where."""
    discipline_filter = request.GET.get('discipline', '')
    county_filter = request.GET.get('county', '')

    players = CountyPlayer.objects.filter(
        verification_status='verified',
    ).select_related(
        'discipline', 'discipline__registration', 'verified_by',
    ).order_by('discipline__sport_type', 'discipline__registration__county', 'last_name')

    if discipline_filter:
        players = players.filter(discipline__sport_type=discipline_filter)
    if county_filter:
        players = players.filter(discipline__registration__county=county_filter)

    disciplines = CountyDiscipline.objects.values_list('sport_type', flat=True).distinct()
    counties = CountyRegistration.objects.values_list('county', flat=True).order_by('county')

    return render(request, 'portal/secretary_general/verified_players.html', {
        'players': players,
        'disciplines': disciplines,
        'counties': counties,
        'discipline_filter': discipline_filter,
        'county_filter': county_filter,
        'total': players.count(),
    })
