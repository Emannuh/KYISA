# admin_dashboard/admin_views.py — KYISA CMS
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from competitions.models import Competition, Fixture, Pool, PoolTeam, Venue, FixtureStatus

ADMIN_ROLES = ('admin', 'competition_manager', 'coordinator', 'soccer_coordinator',
               'handball_coordinator', 'basketball_coordinator', 'volleyball_coordinator')


def _deduplicate_fixtures(competition):
    """Remove duplicate fixtures for a competition, keeping the one with results or the oldest."""
    from django.db.models import Q
    pools = Pool.objects.filter(competition=competition)
    any_deleted = False

    for pool in pools:
        fixtures = Fixture.objects.filter(competition=competition, pool=pool, is_knockout=False)
        seen = set()
        to_delete = []
        for fx in fixtures.order_by('created_at'):
            key = tuple(sorted([fx.home_team_id, fx.away_team_id]))
            if key in seen:
                # Duplicate — delete the one without results
                if fx.home_score is None and fx.away_score is None:
                    to_delete.append(fx.pk)
                else:
                    # This dupe has results, delete earlier one without results
                    earlier = Fixture.objects.filter(
                        competition=competition, pool=pool, is_knockout=False,
                        home_score__isnull=True, away_score__isnull=True,
                    ).filter(
                        Q(home_team_id=key[0], away_team_id=key[1]) |
                        Q(home_team_id=key[1], away_team_id=key[0])
                    ).exclude(pk=fx.pk)
                    to_delete.extend(earlier.values_list('pk', flat=True))
            else:
                seen.add(key)

        if to_delete:
            Fixture.objects.filter(pk__in=to_delete).delete()
            any_deleted = True

    # Also dedup knockout fixtures by round+position
    ko_fixtures = Fixture.objects.filter(competition=competition, is_knockout=True)
    ko_seen = set()
    ko_delete = []
    for fx in ko_fixtures.order_by('created_at'):
        key = (fx.knockout_round, fx.bracket_position)
        if key in ko_seen:
            if fx.home_score is None and fx.away_score is None:
                ko_delete.append(fx.pk)
        else:
            ko_seen.add(key)
    if ko_delete:
        Fixture.objects.filter(pk__in=ko_delete).delete()
        any_deleted = True

    # Recalculate standings for all pools after cleanup
    if any_deleted:
        from matches.stats_engine import recalculate_pool_standings
        for pool in pools:
            recalculate_pool_standings(pool)

def admin_or_cm_required(view_func):
    """Allow staff OR users with admin/coordinator roles."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.conf import settings
            from django.shortcuts import redirect as _redirect
            return _redirect(settings.LOGIN_URL or 'web_login')
        if request.user.is_staff or request.user.role in ADMIN_ROLES or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden('You do not have permission to access this page.')
    return wrapper


@admin_or_cm_required
def generate_fixtures_admin(request):
    """Generate fixtures for a competition (placeholder)."""
    competitions = Competition.objects.all().order_by('name')

    if request.method == 'POST':
        comp_id = request.POST.get('competition_id')
        if comp_id:
            messages.info(request, "Fixture generation coming soon.")
        return redirect('generate_fixtures_admin')

    return render(request, 'admin_dashboard/generate_fixtures.html', {
        'competitions': competitions,
    })


@admin_or_cm_required
def admin_manage_fixtures_view(request):
    """Admin: select a competition to manage its fixtures."""
    competitions = Competition.objects.all().order_by('-season', 'name')
    return render(request, 'admin_dashboard/manage_fixtures_select.html', {
        'competitions': competitions,
    })


@admin_or_cm_required
def admin_competition_fixtures_view(request, pk):
    """Admin: view all pools and fixtures for a competition, enter results."""
    competition = get_object_or_404(Competition, pk=pk)

    # ── Auto-clean duplicate fixtures (same matchup in same pool) ──
    _deduplicate_fixtures(competition)

    pools = Pool.objects.filter(competition=competition).prefetch_related(
        'pool_teams__team', 'fixtures__home_team', 'fixtures__away_team', 'fixtures__venue'
    )

    pool_data = []
    for pool in pools:
        teams = pool.pool_teams.select_related('team').all()
        sorted_teams = sorted(
            teams,
            key=lambda pt: (pt.points, pt.goal_difference, pt.goals_for),
            reverse=True,
        )
        fixtures = pool.fixtures.select_related(
            'home_team', 'away_team', 'venue'
        ).order_by('match_date', 'kickoff_time')
        pool_data.append({
            'pool': pool,
            'teams': sorted_teams,
            'fixtures': fixtures,
        })

    # Knockout fixtures (no pool)
    knockout_fixtures = Fixture.objects.filter(
        competition=competition, is_knockout=True
    ).select_related(
        'home_team', 'away_team', 'venue', 'winner'
    ).order_by('knockout_round', 'bracket_position', 'match_date')

    # Unassigned fixtures (no pool, not knockout)
    unassigned_fixtures = Fixture.objects.filter(
        competition=competition, pool__isnull=True, is_knockout=False
    ).select_related('home_team', 'away_team', 'venue').order_by('match_date')

    return render(request, 'admin_dashboard/competition_fixtures.html', {
        'competition': competition,
        'pool_data': pool_data,
        'knockout_fixtures': knockout_fixtures,
        'unassigned_fixtures': unassigned_fixtures,
        'status_choices': FixtureStatus.choices,
    })


@admin_or_cm_required
def admin_edit_fixture_view(request, pk, fixture_pk):
    """Admin: edit a fixture — date, time, venue, status, scores and results."""
    competition = get_object_or_404(Competition, pk=pk)
    fixture = get_object_or_404(Fixture, pk=fixture_pk, competition=competition)
    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')

    if request.method == 'POST':
        original_status = fixture.status
        original_home_score = fixture.home_score
        original_away_score = fixture.away_score

        # Date and time
        fixture.match_date = request.POST.get('match_date', fixture.match_date)
        kickoff = request.POST.get('kickoff_time', '')
        if kickoff:
            from datetime import datetime
            try:
                fixture.kickoff_time = datetime.strptime(kickoff, '%H:%M').time()
            except ValueError:
                pass

        # Venue
        venue_id = request.POST.get('venue_id', '')
        if venue_id:
            try:
                fixture.venue = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                pass
        else:
            fixture.venue = None

        # Status
        status = request.POST.get('status', fixture.status)
        if status:
            fixture.status = status

        # Scores
        home_score = request.POST.get('home_score', '')
        away_score = request.POST.get('away_score', '')
        if home_score != '':
            fixture.home_score = int(home_score)
        if away_score != '':
            fixture.away_score = int(away_score)

        # For knockout: team reassignment
        if fixture.is_knockout:
            from teams.models import Team
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

            # Extra time & penalties
            home_score_et = request.POST.get('home_score_et', '')
            away_score_et = request.POST.get('away_score_et', '')
            home_penalties = request.POST.get('home_penalties', '')
            away_penalties = request.POST.get('away_penalties', '')
            if home_score_et != '':
                fixture.home_score_et = int(home_score_et)
            if away_score_et != '':
                fixture.away_score_et = int(away_score_et)
            if home_penalties != '':
                fixture.home_penalties = int(home_penalties)
            if away_penalties != '':
                fixture.away_penalties = int(away_penalties)

        score_changed = (
            fixture.home_score != original_home_score or
            fixture.away_score != original_away_score
        )
        status_changed = fixture.status != original_status

        # Auto-set completed when scores are entered
        if score_changed and fixture.home_score is not None and fixture.away_score is not None:
            if fixture.status not in ('completed', 'cancelled'):
                fixture.status = 'completed'
                status_changed = True

        fixture.save()

        # Log and recalculate if scores/status changed
        if score_changed or status_changed:
            from admin_dashboard.models import ActivityLog
            ActivityLog.objects.create(
                user=request.user,
                action='RESULT_OVERRIDE',
                description=(
                    f'{request.user.get_full_name()} updated results for '
                    f'{fixture} via admin dashboard. '
                    f'Score: {original_home_score}-{original_away_score} → '
                    f'{fixture.home_score}-{fixture.away_score}, '
                    f'Status: {original_status} → {fixture.status}'
                ),
                object_repr=str(fixture),
                ip_address=request.META.get('REMOTE_ADDR', ''),
                extra_data={
                    'admin_edit': True,
                    'status_before': original_status,
                    'status_after': fixture.status,
                    'home_score_before': original_home_score,
                    'away_score_before': original_away_score,
                    'home_score_after': fixture.home_score,
                    'away_score_after': fixture.away_score,
                },
            )

            # Auto-update pool standings
            from matches.stats_engine import recalculate_pool_standings
            if fixture.pool:
                recalculate_pool_standings(fixture.pool)
            if fixture.is_knockout and fixture.home_score is not None and fixture.away_score is not None:
                fixture.determine_winner()
                fixture.save(update_fields=['winner'])

        messages.success(request, f'Fixture updated: {fixture}')
        return redirect('admin_competition_fixtures', pk=pk)

    from teams.models import Team
    teams = Team.objects.filter(
        status='registered', payment_confirmed=True
    ).order_by('name') if fixture.is_knockout else None

    return render(request, 'admin_dashboard/admin_edit_fixture.html', {
        'competition': competition,
        'fixture': fixture,
        'venues': venues,
        'teams': teams,
        'status_choices': FixtureStatus.choices,
    })


@admin_or_cm_required
def admin_quick_result_view(request, pk, fixture_pk):
    """Admin: quick inline result update (AJAX-friendly)."""
    if request.method != 'POST':
        return redirect('admin_competition_fixtures', pk=pk)

    competition = get_object_or_404(Competition, pk=pk)
    fixture = get_object_or_404(Fixture, pk=fixture_pk, competition=competition)

    original_home_score = fixture.home_score
    original_away_score = fixture.away_score
    original_status = fixture.status

    home_score = request.POST.get('home_score', '')
    away_score = request.POST.get('away_score', '')

    if home_score == '' or away_score == '':
        messages.error(request, 'Both scores are required.')
        return redirect('admin_competition_fixtures', pk=pk)

    fixture.home_score = int(home_score)
    fixture.away_score = int(away_score)
    if fixture.status not in ('completed', 'cancelled'):
        fixture.status = 'completed'
    fixture.save()

    # Log
    from admin_dashboard.models import ActivityLog
    ActivityLog.objects.create(
        user=request.user,
        action='RESULT_OVERRIDE',
        description=(
            f'{request.user.get_full_name()} entered result for '
            f'{fixture} via admin quick-entry. '
            f'Score: {fixture.home_score}-{fixture.away_score}'
        ),
        object_repr=str(fixture),
        ip_address=request.META.get('REMOTE_ADDR', ''),
        extra_data={
            'admin_quick_result': True,
            'home_score_before': original_home_score,
            'away_score_before': original_away_score,
            'home_score_after': fixture.home_score,
            'away_score_after': fixture.away_score,
        },
    )

    # Auto-update pool standings
    from matches.stats_engine import recalculate_pool_standings
    if fixture.pool:
        recalculate_pool_standings(fixture.pool)
    if fixture.is_knockout and fixture.home_score is not None and fixture.away_score is not None:
        fixture.determine_winner()
        fixture.save(update_fields=['winner'])

    messages.success(
        request,
        f'Result saved: {fixture.home_team} {fixture.home_score} - '
        f'{fixture.away_score} {fixture.away_team}'
    )
    return redirect('admin_competition_fixtures', pk=pk)


@admin_or_cm_required
def admin_create_knockout_fixture_view(request, pk):
    """Admin: create a new knockout fixture for a competition."""
    from teams.models import Team
    from competitions.models import KnockoutRound

    competition = get_object_or_404(Competition, pk=pk)
    venues = Venue.objects.filter(is_active=True).order_by('county', 'name')
    teams = Team.objects.filter(
        status='registered', payment_confirmed=True
    ).order_by('name')

    if request.method == 'POST':
        knockout_round = request.POST.get('knockout_round', '')
        bracket_position = request.POST.get('bracket_position', '')
        home_team_id = request.POST.get('home_team_id', '')
        away_team_id = request.POST.get('away_team_id', '')
        venue_id = request.POST.get('venue_id', '')
        match_date = request.POST.get('match_date', '')
        kickoff_time = request.POST.get('kickoff_time', '')
        status = request.POST.get('status', 'pending')

        if not match_date or not kickoff_time or not knockout_round:
            messages.error(request, 'Knockout round, match date, and kickoff time are required.')
            return redirect('admin_create_knockout_fixture', pk=pk)

        fixture_data = {
            'competition': competition,
            'is_knockout': True,
            'knockout_round': knockout_round,
            'match_date': match_date,
            'status': status,
            'created_by': request.user,
        }

        from datetime import datetime
        try:
            fixture_data['kickoff_time'] = datetime.strptime(kickoff_time, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Invalid kickoff time format.')
            return redirect('admin_create_knockout_fixture', pk=pk)

        if bracket_position:
            fixture_data['bracket_position'] = int(bracket_position)

        if home_team_id:
            try:
                fixture_data['home_team'] = Team.objects.get(pk=home_team_id)
            except Team.DoesNotExist:
                pass

        if away_team_id:
            try:
                fixture_data['away_team'] = Team.objects.get(pk=away_team_id)
            except Team.DoesNotExist:
                pass

        if venue_id:
            try:
                fixture_data['venue'] = Venue.objects.get(pk=venue_id)
            except Venue.DoesNotExist:
                pass

        # Require at least placeholder teams
        if 'home_team' not in fixture_data or 'away_team' not in fixture_data:
            messages.error(request, 'Both home and away teams are required.')
            return redirect('admin_create_knockout_fixture', pk=pk)

        # Check for duplicate knockout fixture (same round + position)
        if bracket_position:
            existing = Fixture.objects.filter(
                competition=competition,
                is_knockout=True,
                knockout_round=knockout_round,
                bracket_position=int(bracket_position),
            ).exists()
            if existing:
                messages.warning(request, f'A fixture already exists for {knockout_round} position {bracket_position}.')

        fixture = Fixture.objects.create(**fixture_data)

        # Log activity
        from admin_dashboard.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            action='FIXTURE_CREATE',
            description=(
                f'{request.user.get_full_name()} created knockout fixture: '
                f'{fixture} ({fixture.get_knockout_round_display()})'
            ),
            object_repr=str(fixture),
            ip_address=request.META.get('REMOTE_ADDR', ''),
            extra_data={'knockout': True, 'round': knockout_round},
        )

        messages.success(request, f'Knockout fixture created: {fixture}')
        return redirect('admin_competition_fixtures', pk=pk)

    return render(request, 'admin_dashboard/create_knockout_fixture.html', {
        'competition': competition,
        'venues': venues,
        'teams': teams,
        'knockout_rounds': KnockoutRound.choices,
        'status_choices': FixtureStatus.choices,
    })


@admin_or_cm_required
def admin_delete_knockout_fixture_view(request, pk, fixture_pk):
    """Admin: delete a knockout fixture (only if no result entered)."""
    competition = get_object_or_404(Competition, pk=pk)
    fixture = get_object_or_404(
        Fixture, pk=fixture_pk, competition=competition, is_knockout=True
    )

    if request.method == 'POST':
        label = str(fixture)
        from admin_dashboard.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            action='FIXTURE_DELETE',
            description=f'{request.user.get_full_name()} deleted knockout fixture: {label}',
            object_repr=label,
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )
        fixture.delete()
        messages.success(request, f'Knockout fixture deleted: {label}')
        return redirect('admin_knockout_hub')

    return render(request, 'admin_dashboard/delete_knockout_fixture.html', {
        'competition': competition,
        'fixture': fixture,
    })


@admin_or_cm_required
def admin_knockout_hub_view(request):
    """Admin: knockout management hub — view all knockout fixtures across all competitions."""
    from competitions.models import KnockoutRound

    competitions = Competition.objects.all().order_by('-season', 'name')
    competition_data = []

    for comp in competitions:
        knockouts = Fixture.objects.filter(
            competition=comp, is_knockout=True
        ).select_related(
            'home_team', 'away_team', 'venue', 'winner'
        ).order_by('knockout_round', 'bracket_position', 'match_date')

        if knockouts.exists() or True:  # always show so admin can create
            competition_data.append({
                'competition': comp,
                'knockout_fixtures': knockouts,
                'count': knockouts.count(),
            })

    return render(request, 'admin_dashboard/knockout_hub.html', {
        'competition_data': competition_data,
        'knockout_rounds': KnockoutRound.choices,
    })


@admin_or_cm_required
def admin_bulk_delete_knockout_view(request, pk):
    """Admin: delete ALL knockout fixtures (without results) for a competition."""
    competition = get_object_or_404(Competition, pk=pk)

    if request.method == 'POST':
        knockouts = Fixture.objects.filter(
            competition=competition,
            is_knockout=True,
        )
        count = knockouts.count()

        # Log activity
        from admin_dashboard.models import ActivityLog
        ActivityLog.objects.create(
            user=request.user,
            action='FIXTURE_DELETE',
            description=(
                f'{request.user.get_full_name()} bulk-deleted {count} knockout '
                f'fixture(s) from {competition.name}'
            ),
            object_repr=f'{competition.name} knockouts',
            ip_address=request.META.get('REMOTE_ADDR', ''),
        )

        knockouts.delete()
        messages.success(request, f'Deleted {count} knockout fixture(s) from {competition.name}.')

    return redirect('admin_knockout_hub')
