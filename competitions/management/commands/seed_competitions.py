"""
Management command to seed the default KYISA 2026 competitions.
Creates 10 competitions (men + women) for the 5 core disciplines.

Usage:
    python manage.py seed_competitions
    python manage.py seed_competitions --season 2026
"""
from django.core.management.base import BaseCommand
from competitions.models import Competition, SportType, GenderChoice, CompetitionFormat, AgeGroup


DEFAULT_COMPETITIONS = [
    # Football
    {
        "name": "Football (Men) — KYISA {season}",
        "sport_type": SportType.FOOTBALL_MEN,
        "gender": GenderChoice.MEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Men's football competition — KYISA {season} edition.",
    },
    {
        "name": "Football (Women) — KYISA {season}",
        "sport_type": SportType.FOOTBALL_WOMEN,
        "gender": GenderChoice.WOMEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Women's football competition — KYISA {season} edition.",
    },
    # Volleyball
    {
        "name": "Volleyball (Men) — KYISA {season}",
        "sport_type": SportType.VOLLEYBALL_MEN,
        "gender": GenderChoice.MEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Men's volleyball competition — KYISA {season} edition.",
    },
    {
        "name": "Volleyball (Women) — KYISA {season}",
        "sport_type": SportType.VOLLEYBALL_WOMEN,
        "gender": GenderChoice.WOMEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Women's volleyball competition — KYISA {season} edition.",
    },
    # Handball
    {
        "name": "Handball (Men) — KYISA {season}",
        "sport_type": SportType.HANDBALL_MEN,
        "gender": GenderChoice.MEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Men's handball competition — KYISA {season} edition.",
    },
    {
        "name": "Handball (Women) — KYISA {season}",
        "sport_type": SportType.HANDBALL_WOMEN,
        "gender": GenderChoice.WOMEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Women's handball competition — KYISA {season} edition.",
    },
    # Basketball 5x5
    {
        "name": "Basketball 5×5 (Men) — KYISA {season}",
        "sport_type": SportType.BASKETBALL_MEN,
        "gender": GenderChoice.MEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Men's basketball 5×5 competition — KYISA {season} edition.",
    },
    {
        "name": "Basketball 5×5 (Women) — KYISA {season}",
        "sport_type": SportType.BASKETBALL_WOMEN,
        "gender": GenderChoice.WOMEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Women's basketball 5×5 competition — KYISA {season} edition.",
    },
    # Basketball 3x3
    {
        "name": "Basketball 3×3 (Men) — KYISA {season}",
        "sport_type": SportType.BASKETBALL_3X3_MEN,
        "gender": GenderChoice.MEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Men's basketball 3×3 competition — KYISA {season} edition.",
    },
    {
        "name": "Basketball 3×3 (Women) — KYISA {season}",
        "sport_type": SportType.BASKETBALL_3X3_WOMEN,
        "gender": GenderChoice.WOMEN,
        "format_type": CompetitionFormat.GROUP_AND_KNOCKOUT,
        "max_teams": 16,
        "teams_per_group": 4,
        "qualify_from_group": 2,
        "description": "Women's basketball 3×3 competition — KYISA {season} edition.",
    },
]


class Command(BaseCommand):
    help = "Seed KYISA default competitions (10 disciplines: men + women)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--season", type=str, default="2026",
            help="Season year (default: 2026)",
        )
        parser.add_argument(
            "--start-date", type=str, default="2026-04-13",
            help="Start date YYYY-MM-DD (default: 2026-04-13)",
        )
        parser.add_argument(
            "--end-date", type=str, default="2026-04-19",
            help="End date YYYY-MM-DD (default: 2026-04-19)",
        )

    def handle(self, *args, **options):
        season = options["season"]
        start_date = options["start_date"]
        end_date = options["end_date"]

        created_count = 0
        skipped_count = 0

        for comp_data in DEFAULT_COMPETITIONS:
            name = comp_data["name"].format(season=season)
            description = comp_data["description"].format(season=season)

            if Competition.objects.filter(name=name).exists():
                self.stdout.write(self.style.WARNING(f"  SKIP  {name} (already exists)"))
                skipped_count += 1
                continue

            Competition.objects.create(
                name=name,
                sport_type=comp_data["sport_type"],
                gender=comp_data["gender"],
                format_type=comp_data["format_type"],
                season=season,
                age_group=AgeGroup.U23,
                status="registration",
                start_date=start_date,
                end_date=end_date,
                max_teams=comp_data["max_teams"],
                teams_per_group=comp_data["teams_per_group"],
                qualify_from_group=comp_data["qualify_from_group"],
                description=description,
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓  Created: {name}"))
            created_count += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done — {created_count} created, {skipped_count} skipped"
        ))
