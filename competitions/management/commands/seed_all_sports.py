"""
Seed teams, pools, and fixtures for all KYISA 2026 competitions.
Competitions 3-10: Volleyball, Handball, Basketball 5x5, Basketball 3x3
"""
from datetime import date, time, timedelta
from itertools import combinations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from competitions.models import Competition, Pool, PoolTeam, Fixture, Venue, FixtureStatus
from teams.models import Team, County


# Counties participating in each sport (by county name)
VOLLEYBALL_COUNTIES = [
    'Meru', 'Kirinyaga', 'Narok', 'Siaya', 'Kilifi', 'Makueni',
    'Busia', 'Nakuru', 'Laikipia', 'Migori', 'Garissa', 'Nyandarua',
]
HANDBALL_COUNTIES = [
    'Meru', 'Narok', 'Kilifi', 'Busia', 'Nakuru', 'Siaya',
    'Laikipia', 'Makueni', 'Kirinyaga', 'Migori',
]
BASKETBALL_5X5_COUNTIES = [
    'Meru', 'Narok', 'Nakuru', 'Siaya', 'Laikipia', 'Busia',
    'Kirinyaga', 'Makueni', 'Kilifi', 'Migori', 'Nyandarua', 'Garissa',
]
BASKETBALL_3X3_COUNTIES = [
    'Meru', 'Narok', 'Nakuru', 'Siaya', 'Laikipia', 'Busia',
    'Kirinyaga', 'Makueni',
]

# Map competition PK → config
SPORT_CONFIG = {
    # Volleyball Men [3]
    3: {
        'counties': VOLLEYBALL_COUNTIES,
        'suffix': '',
        'pools': {'Pool A': 4, 'Pool B': 4, 'Pool C': 4},
        'start_date': date(2026, 4, 18),
        'kickoff': time(9, 0),
    },
    # Volleyball Women [4]
    4: {
        'counties': VOLLEYBALL_COUNTIES[:8],
        'suffix': ' (W)',
        'pools': {'Pool A': 4, 'Pool B': 4},
        'start_date': date(2026, 4, 18),
        'kickoff': time(11, 0),
    },
    # Handball Men [5]
    5: {
        'counties': HANDBALL_COUNTIES,
        'suffix': '',
        'pools': {'Pool A': 5, 'Pool B': 5},
        'start_date': date(2026, 4, 19),
        'kickoff': time(8, 0),
    },
    # Handball Women [6]
    6: {
        'counties': HANDBALL_COUNTIES[:8],
        'suffix': ' (W)',
        'pools': {'Pool A': 4, 'Pool B': 4},
        'start_date': date(2026, 4, 19),
        'kickoff': time(10, 0),
    },
    # Basketball 5x5 Men [7]
    7: {
        'counties': BASKETBALL_5X5_COUNTIES,
        'suffix': '',
        'pools': {'Pool A': 4, 'Pool B': 4, 'Pool C': 4},
        'start_date': date(2026, 4, 20),
        'kickoff': time(9, 0),
    },
    # Basketball 5x5 Women [8]
    8: {
        'counties': BASKETBALL_5X5_COUNTIES[:8],
        'suffix': ' (W)',
        'pools': {'Pool A': 4, 'Pool B': 4},
        'start_date': date(2026, 4, 20),
        'kickoff': time(11, 0),
    },
    # Basketball 3x3 Men [9]
    9: {
        'counties': BASKETBALL_3X3_COUNTIES,
        'suffix': '',
        'pools': {'Pool A': 4, 'Pool B': 4},
        'start_date': date(2026, 4, 21),
        'kickoff': time(9, 0),
    },
    # Basketball 3x3 Women [10]
    10: {
        'counties': BASKETBALL_3X3_COUNTIES[:6],
        'suffix': ' (W)',
        'pools': {'Pool A': 3, 'Pool B': 3},
        'start_date': date(2026, 4, 21),
        'kickoff': time(11, 0),
    },
}


class Command(BaseCommand):
    help = 'Seed teams, pools, and round-robin fixtures for all KYISA 2026 competitions'

    def handle(self, *args, **options):
        venue = Venue.objects.filter(is_active=True).first()

        for comp_pk, config in SPORT_CONFIG.items():
            try:
                competition = Competition.objects.get(pk=comp_pk)
            except Competition.DoesNotExist:
                self.stderr.write(f'Competition {comp_pk} not found, skipping')
                continue

            # Skip if it already has fixtures
            existing = Fixture.objects.filter(competition=competition).count()
            if existing > 0:
                self.stdout.write(f'  {competition.name}: already has {existing} fixtures, skipping')
                continue

            self.stdout.write(f'\n=== {competition.name} ===')

            with transaction.atomic():
                # 1. Create teams
                teams = []
                for county_name in config['counties']:
                    county = County.objects.filter(name=county_name).first()
                    if not county:
                        self.stderr.write(f'  County "{county_name}" not found')
                        continue

                    team_name = f'{county_name}{config["suffix"]}'
                    team, created = Team.objects.get_or_create(
                        name=team_name,
                        competition=competition,
                        defaults={
                            'county': county,
                            'sport_type': competition.sport_type,
                            'status': 'registered',
                            'payment_confirmed': True,
                            'contact_phone': '+254700000000',
                        }
                    )
                    if created:
                        self.stdout.write(f'  + Team: {team_name}')
                    teams.append(team)

                # 2. Create pools and assign teams
                pool_names = list(config['pools'].keys())
                team_idx = 0
                pool_objects = []

                for pool_name, pool_size in config['pools'].items():
                    pool, created = Pool.objects.get_or_create(
                        competition=competition,
                        name=pool_name,
                    )
                    pool_objects.append(pool)
                    if created:
                        self.stdout.write(f'  + Pool: {pool_name}')

                    # Assign teams to pool
                    for _ in range(pool_size):
                        if team_idx >= len(teams):
                            break
                        team = teams[team_idx]
                        PoolTeam.objects.get_or_create(
                            pool=pool,
                            team=team,
                        )
                        team_idx += 1

                # 3. Generate round-robin fixtures per pool
                fixture_count = 0
                current_date = config['start_date']
                kickoff = config['kickoff']

                for pool in pool_objects:
                    pool_teams = [pt.team for pt in PoolTeam.objects.filter(pool=pool).select_related('team')]
                    if len(pool_teams) < 2:
                        continue

                    matchups = list(combinations(pool_teams, 2))
                    for i, (home, away) in enumerate(matchups):
                        # Check for existing
                        exists = Fixture.objects.filter(
                            competition=competition, pool=pool, is_knockout=False
                        ).filter(
                            Q(home_team=home, away_team=away) |
                            Q(home_team=away, away_team=home)
                        ).exists()
                        if exists:
                            continue

                        Fixture.objects.create(
                            competition=competition,
                            pool=pool,
                            home_team=home,
                            away_team=away,
                            venue=venue,
                            match_date=current_date,
                            kickoff_time=kickoff,
                            status=FixtureStatus.CONFIRMED,
                            round_number=fixture_count + 1,
                            is_knockout=False,
                        )
                        fixture_count += 1
                        # Stagger: 3 matches per day
                        if fixture_count % 3 == 0:
                            current_date += timedelta(days=1)

                # Update competition status
                competition.status = 'group_stage'
                competition.save(update_fields=['status'])

                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ {len(teams)} teams, {len(pool_objects)} pools, '
                        f'{fixture_count} fixtures created'
                    )
                )

        self.stdout.write(self.style.SUCCESS('\nDone!'))
