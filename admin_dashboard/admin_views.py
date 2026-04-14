# admin_dashboard/admin_views.py — KYISA CMS
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from competitions.models import Competition, Fixture, Pool, PoolTeam, Venue, FixtureStatus


@staff_member_required
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


@staff_member_required
def admin_manage_fixtures_view(request):
    """Admin: select a competition to manage its fixtures."""
    competitions = Competition.objects.all().order_by('-season', 'name')
    return render(request, 'admin_dashboard/manage_fixtures_select.html', {
        'competitions': competitions,
    })


@staff_member_required
def admin_competition_fixtures_view(request, pk):
    """Admin: view all pools and fixtures for a competition, enter results."""
    competition = get_object_or_404(Competition, pk=pk)

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


@staff_member_required
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


@staff_member_required
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
