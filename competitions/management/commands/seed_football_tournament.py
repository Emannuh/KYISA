"""
Management command to seed the KYISA 11th Edition Football Tournament.
Creates competitions, venues, pools, teams, pool assignments, and all 45 fixtures.

Usage:
    python manage.py seed_football_tournament
    python manage.py seed_football_tournament --clear   # wipe & re-seed
"""
from datetime import date, time
from django.core.management.base import BaseCommand
from django.db import transaction
from competitions.models import (
    Competition, Venue, Pool, PoolTeam, Fixture, FixtureStatus,
    SportType, GenderChoice, CompetitionFormat, AgeGroup, KnockoutRound,
)
from teams.models import Team, County


# ── VENUE DEFINITIONS ─────────────────────────────────────────────────────
VENUES = {
    "Stadium 1": {"county": "Meru", "city": "Meru", "capacity": 5000, "surface": "Natural Grass"},
    "Stadium 2": {"county": "Meru", "city": "Meru", "capacity": 5000, "surface": "Natural Grass"},
    "Ndururumo 1": {"county": "Meru", "city": "Meru", "capacity": 2000, "surface": "Natural Grass"},
    "Ndururumo 2": {"county": "Meru", "city": "Meru", "capacity": 2000, "surface": "Natural Grass"},
    "Ndururumo 3": {"county": "Meru", "city": "Meru", "capacity": 2000, "surface": "Natural Grass"},
}

# ── MEN'S POOLS ───────────────────────────────────────────────────────────
MEN_POOLS = {
    "Pool A": ["Laikipia", "Narok", "Makueni", "Nakuru"],
    "Pool B": ["Wajir", "Kirinyaga", "Mandera", "Kilifi"],
    "Pool C": ["Tharaka Nithi", "Busia", "Tana River", "Siaya"],
    "Pool D": ["Meru", "Migori", "Nyandarua", "Garissa"],
}

# ── WOMEN'S POOLS ─────────────────────────────────────────────────────────
WOMEN_POOLS = {
    "Pool A": ["Laikipia", "Kajiado", "Meru", "Siaya"],
    "Pool B": ["Makueni", "Narok", "Kirinyaga"],
}

# ── ALL 45 FIXTURES ───────────────────────────────────────────────────────
# Format: (match_num, date, time_str, venue, home, away, gender, pool_name,
#           is_knockout, knockout_round, bracket_position)
FIXTURES = [
    # ── TUESDAY 14/04/2026 ─────────────────────────────────
    (1,  "2026-04-14", "14:30", "Stadium 1",   "Laikipia",      "Narok",       "M", "Pool A", False, "", 0),
    (2,  "2026-04-14", "15:00", "Ndururumo 1",  "Wajir",         "Kirinyaga",   "M", "Pool B", False, "", 0),
    (3,  "2026-04-14", "15:00", "Ndururumo 3",  "Tharaka Nithi", "Busia",       "M", "Pool C", False, "", 0),
    (4,  "2026-04-14", "15:00", "Stadium 2",    "Nyandarua",     "Garissa",     "M", "Pool D", False, "", 0),
    (5,  "2026-04-14", "15:00", "Ndururumo 2",  "Laikipia",      "Kajiado",     "W", "Pool A", False, "", 0),

    # ── WEDNESDAY 15/04/2026 ───────────────────────────────
    (6,  "2026-04-15", "09:00", "Stadium 1",    "Makueni",       "Nakuru",      "M", "Pool A", False, "", 0),
    (7,  "2026-04-15", "09:00", "Ndururumo 1",  "Mandera",       "Kilifi",      "M", "Pool B", False, "", 0),
    (8,  "2026-04-15", "09:00", "Ndururumo 3",  "Tana River",    "Siaya",       "M", "Pool C", False, "", 0),
    (9,  "2026-04-15", "09:00", "Stadium 2",    "Meru",          "Migori",      "M", "Pool D", False, "", 0),
    (10, "2026-04-15", "09:00", "Ndururumo 2",  "Meru",          "Siaya",       "W", "Pool A", False, "", 0),
    (11, "2026-04-15", "11:00", "Ndururumo 2",  "Makueni",       "Narok",       "W", "Pool B", False, "", 0),
    (12, "2026-04-15", "13:00", "Stadium 1",    "Laikipia",      "Makueni",     "M", "Pool A", False, "", 0),
    (13, "2026-04-15", "13:00", "Ndururumo 1",  "Wajir",         "Mandera",     "M", "Pool B", False, "", 0),
    (14, "2026-04-15", "13:00", "Ndururumo 3",  "Tharaka Nithi", "Tana River",  "M", "Pool C", False, "", 0),
    (15, "2026-04-15", "13:00", "Stadium 2",    "Meru",          "Nyandarua",   "M", "Pool D", False, "", 0),
    (16, "2026-04-15", "13:00", "Ndururumo 2",  "Laikipia",      "Meru",        "W", "Pool A", False, "", 0),
    (17, "2026-04-15", "15:00", "Stadium 1",    "Narok",         "Nakuru",      "M", "Pool A", False, "", 0),
    (18, "2026-04-15", "15:00", "Ndururumo 1",  "Kirinyaga",     "Kilifi",      "M", "Pool B", False, "", 0),
    (19, "2026-04-15", "15:00", "Ndururumo 3",  "Busia",         "Siaya",       "M", "Pool C", False, "", 0),
    (20, "2026-04-15", "15:00", "Stadium 2",    "Migori",        "Garissa",     "M", "Pool D", False, "", 0),
    (21, "2026-04-15", "15:00", "Ndururumo 2",  "Kajiado",       "Siaya",       "W", "Pool A", False, "", 0),

    # ── THURSDAY 16/04/2026 ────────────────────────────────
    (22, "2026-04-16", "09:00", "Stadium 1",    "Nakuru",        "Laikipia",    "M", "Pool A", False, "", 0),
    (23, "2026-04-16", "09:00", "Ndururumo 1",  "Kilifi",        "Wajir",       "M", "Pool B", False, "", 0),
    (24, "2026-04-16", "09:00", "Ndururumo 3",  "Siaya",         "Tharaka Nithi","M","Pool C", False, "", 0),
    (25, "2026-04-16", "09:00", "Stadium 2",    "Garissa",       "Meru",        "M", "Pool D", False, "", 0),
    (26, "2026-04-16", "09:00", "Ndururumo 2",  "Siaya",         "Laikipia",    "W", "Pool A", False, "", 0),
    (27, "2026-04-16", "11:00", "Ndururumo 2",  "Kirinyaga",     "Makueni",     "W", "Pool B", False, "", 0),
    (28, "2026-04-16", "11:00", "Stadium 1",    "Narok",         "Makueni",     "M", "Pool A", False, "", 0),
    (29, "2026-04-16", "11:00", "Ndururumo 1",  "Kirinyaga",     "Mandera",     "M", "Pool B", False, "", 0),
    (30, "2026-04-16", "11:00", "Ndururumo 3",  "Busia",         "Tana River",  "M", "Pool C", False, "", 0),
    (31, "2026-04-16", "11:00", "Stadium 2",    "Migori",        "Nyandarua",   "M", "Pool D", False, "", 0),
    (32, "2026-04-16", "13:00", "Ndururumo 2",  "Kajiado",       "Meru",        "W", "Pool A", False, "", 0),
    (33, "2026-04-16", "15:00", "Ndururumo 2",  "Narok",         "Kirinyaga",   "W", "Pool B", False, "", 0),

    # ── THURSDAY 16/04 KNOCKOUT: MEN QFs ───────────────────
    (34, "2026-04-16", "15:00", "Stadium 1",    None, None,      "M", "", True, KnockoutRound.QUARTERFINAL, 1),
    (35, "2026-04-16", "15:00", "Ndururumo 1",  None, None,      "M", "", True, KnockoutRound.QUARTERFINAL, 2),
    (36, "2026-04-16", "15:00", "Ndururumo 3",  None, None,      "M", "", True, KnockoutRound.QUARTERFINAL, 3),
    (37, "2026-04-16", "15:00", "Stadium 2",    None, None,      "M", "", True, KnockoutRound.QUARTERFINAL, 4),

    # ── FRIDAY 17/04/2026 ──────────────────────────────────
    # Women Semis
    (38, "2026-04-17", "09:00", "Ndururumo 1",  None, None,      "W", "", True, KnockoutRound.SEMIFINAL, 1),
    (39, "2026-04-17", "09:00", "Ndururumo 3",  None, None,      "W", "", True, KnockoutRound.SEMIFINAL, 2),
    # Men Semis
    (40, "2026-04-17", "09:00", "Stadium 1",    None, None,      "M", "", True, KnockoutRound.SEMIFINAL, 1),
    (41, "2026-04-17", "09:00", "Stadium 2",    None, None,      "M", "", True, KnockoutRound.SEMIFINAL, 2),
    # Women 3rd place
    (42, "2026-04-17", "15:00", "Stadium 2",    None, None,      "W", "", True, KnockoutRound.THIRD_PLACE, 1),
    # Men 3rd place
    (43, "2026-04-17", "15:00", "Stadium 1",    None, None,      "M", "", True, KnockoutRound.THIRD_PLACE, 1),

    # ── SATURDAY 18/04/2026 ────────────────────────────────
    # Women Final
    (44, "2026-04-18", "10:30", "Stadium 1",    None, None,      "W", "", True, KnockoutRound.FINAL, 1),
    # Men Final
    (45, "2026-04-18", "14:00", "Stadium 1",    None, None,      "M", "", True, KnockoutRound.FINAL, 1),
]

# Knockout match descriptions (for display)
KNOCKOUT_DESCRIPTIONS = {
    34: "Winner A vs Runner-up B",
    35: "Winner B vs Runner-up A",
    36: "Winner C vs Runner-up D",
    37: "Winner D vs Runner-up C",
    38: "Winner A vs Runner-up B",
    39: "Winner B vs Runner-up A",
    40: "Winner QF1 vs Winner QF3",
    41: "Winner QF2 vs Winner QF4",
    42: "Loser SF1 vs Loser SF2",
    43: "Loser SF1 vs Loser SF2",
    44: "Winner SF1 vs Winner SF2",
    45: "Winner SF1 vs Winner SF2",
}


class Command(BaseCommand):
    help = "Seed the KYISA 11th Edition Football Tournament (Men + Women)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Clear existing football tournament data before seeding",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["clear"]:
            self._clear()

        # 1. Create venues
        venues = self._create_venues()

        # 2. Create competitions
        men_comp = self._create_competition(
            "Football (Men) — KYISA 2026",
            SportType.FOOTBALL_MEN, GenderChoice.MEN,
            max_teams=16, teams_per_group=4,
        )
        women_comp = self._create_competition(
            "Football (Women) — KYISA 2026",
            SportType.FOOTBALL_WOMEN, GenderChoice.WOMEN,
            max_teams=8, teams_per_group=4,
        )

        # 3. Create teams (get_or_create by county name + sport type)
        all_counties = set()
        for pool_teams in MEN_POOLS.values():
            all_counties.update(pool_teams)
        for pool_teams in WOMEN_POOLS.values():
            all_counties.update(pool_teams)

        county_objs = {}
        for county_name in all_counties:
            county_obj, _ = County.objects.get_or_create(
                name=county_name,
                defaults={"code": county_name[:3].upper(), "is_active": True},
            )
            county_objs[county_name] = county_obj

        men_teams = {}
        for county_name in set(c for teams in MEN_POOLS.values() for c in teams):
            team, _ = Team.objects.get_or_create(
                name=county_name,
                sport_type=SportType.FOOTBALL_MEN,
                defaults={
                    "county": county_objs[county_name],
                    "competition": men_comp,
                    "status": "registered",
                    "payment_confirmed": True,
                    "contact_phone": "+254700000000",
                },
            )
            # Ensure registered + paid
            if team.status != "registered" or not team.payment_confirmed:
                team.status = "registered"
                team.payment_confirmed = True
                team.competition = men_comp
                team.save(update_fields=["status", "payment_confirmed", "competition"])
            men_teams[county_name] = team

        women_teams = {}
        for county_name in set(c for teams in WOMEN_POOLS.values() for c in teams):
            team_name = f"{county_name} (W)"
            team, _ = Team.objects.get_or_create(
                name=team_name,
                sport_type=SportType.FOOTBALL_WOMEN,
                defaults={
                    "county": county_objs[county_name],
                    "competition": women_comp,
                    "status": "registered",
                    "payment_confirmed": True,
                    "contact_phone": "+254700000000",
                },
            )
            if team.status != "registered" or not team.payment_confirmed:
                team.status = "registered"
                team.payment_confirmed = True
                team.competition = women_comp
                team.save(update_fields=["status", "payment_confirmed", "competition"])
            women_teams[county_name] = team

        # 4. Create pools and assign teams
        self._create_pools(men_comp, MEN_POOLS, men_teams)
        self._create_pools(women_comp, WOMEN_POOLS, women_teams)

        # We need TBD placeholder teams for knockout fixtures
        tbd_home_m, _ = Team.objects.get_or_create(
            name="TBD (M Home)", sport_type=SportType.FOOTBALL_MEN,
            defaults={"county": county_objs["Meru"], "status": "registered",
                       "payment_confirmed": True, "contact_phone": "+254700000000"},
        )
        tbd_away_m, _ = Team.objects.get_or_create(
            name="TBD (M Away)", sport_type=SportType.FOOTBALL_MEN,
            defaults={"county": county_objs["Meru"], "status": "registered",
                       "payment_confirmed": True, "contact_phone": "+254700000000"},
        )
        tbd_home_w, _ = Team.objects.get_or_create(
            name="TBD (W Home)", sport_type=SportType.FOOTBALL_WOMEN,
            defaults={"county": county_objs["Meru"], "status": "registered",
                       "payment_confirmed": True, "contact_phone": "+254700000000"},
        )
        tbd_away_w, _ = Team.objects.get_or_create(
            name="TBD (W Away)", sport_type=SportType.FOOTBALL_WOMEN,
            defaults={"county": county_objs["Meru"], "status": "registered",
                       "payment_confirmed": True, "contact_phone": "+254700000000"},
        )

        # 5. Create all 45 fixtures
        fixture_count = 0
        for fx in FIXTURES:
            (match_num, match_date_str, time_str, venue_name,
             home_name, away_name, gender, pool_name,
             is_knockout, knockout_round, bracket_pos) = fx

            match_date_val = date.fromisoformat(match_date_str)
            h, m = time_str.split(":")
            kickoff = time(int(h), int(m))
            venue = venues.get(venue_name)

            if gender == "M":
                comp = men_comp
                if is_knockout:
                    home_team = tbd_home_m
                    away_team = tbd_away_m
                    pool = None
                else:
                    home_team = men_teams[home_name]
                    away_team = men_teams[away_name]
                    pool = Pool.objects.get(competition=comp, name=pool_name)
            else:
                comp = women_comp
                if is_knockout:
                    home_team = tbd_home_w
                    away_team = tbd_away_w
                    pool = None
                else:
                    home_team = women_teams[home_name]
                    away_team = women_teams[away_name]
                    pool = Pool.objects.get(competition=comp, name=pool_name)

            Fixture.objects.create(
                competition=comp,
                pool=pool,
                home_team=home_team,
                away_team=away_team,
                venue=venue,
                match_date=match_date_val,
                kickoff_time=kickoff,
                status=FixtureStatus.CONFIRMED,
                round_number=match_num,
                is_knockout=is_knockout,
                knockout_round=knockout_round if is_knockout else "",
                bracket_position=bracket_pos if is_knockout else None,
            )
            fixture_count += 1

        # 6. Update competition status
        men_comp.status = "group_stage"
        men_comp.save(update_fields=["status"])
        women_comp.status = "group_stage"
        women_comp.save(update_fields=["status"])

        self.stdout.write(self.style.SUCCESS(
            f"✅ Tournament seeded: {fixture_count} fixtures, "
            f"{len(men_teams)} men's teams, {len(women_teams)} women's teams, "
            f"{len(venues)} venues"
        ))

    def _clear(self):
        """Remove existing football tournament data."""
        Fixture.objects.filter(
            competition__sport_type__in=[SportType.FOOTBALL_MEN, SportType.FOOTBALL_WOMEN],
            competition__season="2026",
        ).delete()
        PoolTeam.objects.filter(
            pool__competition__sport_type__in=[SportType.FOOTBALL_MEN, SportType.FOOTBALL_WOMEN],
            pool__competition__season="2026",
        ).delete()
        Pool.objects.filter(
            competition__sport_type__in=[SportType.FOOTBALL_MEN, SportType.FOOTBALL_WOMEN],
            competition__season="2026",
        ).delete()
        # Don't delete teams/counties — they may be shared
        self.stdout.write(self.style.WARNING("⚠ Cleared existing football fixtures, pools, pool teams"))

    def _create_venues(self):
        venues = {}
        for name, info in VENUES.items():
            venue, _ = Venue.objects.get_or_create(
                name=name,
                defaults=info,
            )
            venues[name] = venue
        return venues

    def _create_competition(self, name, sport_type, gender, max_teams, teams_per_group):
        comp, created = Competition.objects.get_or_create(
            name=name,
            defaults={
                "sport_type": sport_type,
                "gender": gender,
                "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
                "season": "2026",
                "age_group": AgeGroup.U23,
                "start_date": date(2026, 4, 14),
                "end_date": date(2026, 4, 18),
                "max_teams": max_teams,
                "teams_per_group": teams_per_group,
                "qualify_from_group": 2,
                "description": f"KYISA 11th Edition — {sport_type}",
            },
        )
        if not created:
            comp.start_date = date(2026, 4, 14)
            comp.end_date = date(2026, 4, 18)
            comp.save(update_fields=["start_date", "end_date"])
        return comp

    def _create_pools(self, competition, pools_dict, team_lookup):
        for pool_name, county_names in pools_dict.items():
            pool, _ = Pool.objects.get_or_create(
                competition=competition,
                name=pool_name,
            )
            for county_name in county_names:
                team = team_lookup[county_name]
                PoolTeam.objects.get_or_create(
                    pool=pool,
                    team=team,
                )
