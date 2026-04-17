"""
Data migration — seed Handball (Men & Women) competitions, teams, pools,
standings, and completed fixtures from the 14-17 April 2026 results.

Teams: Makueni, Laikipia, Siaya (both genders)
Scoring: IHF standard — Win = 2 pts, Draw = 1, Loss = 0
"""
import datetime
from django.db import migrations


def seed_handball(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    Pool = apps.get_model("competitions", "Pool")
    PoolTeam = apps.get_model("competitions", "PoolTeam")
    Fixture = apps.get_model("competitions", "Fixture")
    Team = apps.get_model("teams", "Team")
    County = apps.get_model("teams", "County")

    # ── helpers ──────────────────────────────────────────────────
    def get_county(name):
        return County.objects.get(name=name)

    def ensure_team(county, sport_type, comp):
        """Get or create a handball team for the county."""
        name = county.name
        team, _ = Team.objects.get_or_create(
            name=name,
            sport_type=sport_type,
            defaults={
                "county": county,
                "competition": comp,
                "status": "registered",
                "payment_confirmed": True,
                "contact_phone": "+254700000000",
            },
        )
        # ensure linked to this competition
        if team.competition_id != comp.pk:
            team.competition = comp
            team.save(update_fields=["competition"])
        return team

    def make_fixture(comp, pool, home, away, h_score, a_score, date, time_str):
        hour, minute = map(int, time_str.split(":"))
        Fixture.objects.create(
            competition=comp,
            pool=pool,
            home_team=home,
            away_team=away,
            home_score=h_score,
            away_score=a_score,
            match_date=date,
            kickoff_time=datetime.time(hour, minute),
            status="completed",
            is_knockout=False,
        )

    # ── counties ─────────────────────────────────────────────────
    makueni_c = get_county("Makueni")
    laikipia_c = get_county("Laikipia")
    siaya_c = get_county("Siaya")

    # ── dates ────────────────────────────────────────────────────
    tue = datetime.date(2026, 4, 14)
    wed = datetime.date(2026, 4, 15)
    thu = datetime.date(2026, 4, 16)
    fri = datetime.date(2026, 4, 17)

    # ═══════════════════════════════════════════════════════════
    #  MEN'S HANDBALL
    # ═══════════════════════════════════════════════════════════
    men_comp, _ = Competition.objects.get_or_create(
        name="Handball (Men) — KYISA 2026",
        defaults={
            "sport_type": "handball_men",
            "gender": "men",
            "format_type": "group_stage",
            "season": "2026",
            "age_group": "U23",
            "status": "group_stage",
            "is_exhibition": True,
            "start_date": tue,
            "end_date": fri,
            "max_teams": 3,
            "teams_per_group": 3,
            "qualify_from_group": 1,
        },
    )
    # Make sure status is group_stage so tables show on homepage
    if men_comp.status != "group_stage":
        men_comp.status = "group_stage"
        men_comp.format_type = "group_stage"
        men_comp.is_exhibition = True
        men_comp.save(update_fields=["status", "format_type", "is_exhibition"])

    mak_m = ensure_team(makueni_c, "handball_men", men_comp)
    lai_m = ensure_team(laikipia_c, "handball_men", men_comp)
    sia_m = ensure_team(siaya_c, "handball_men", men_comp)

    men_pool, _ = Pool.objects.get_or_create(
        competition=men_comp, name="Group A",
    )

    # Men standings (calculated from 7 results)
    # Siaya:    P4  W4  D0  L0  GF135  GA94   GD+41  Pts8
    # Makueni:  P5  W3  D0  L2  GF117  GA125  GD-8   Pts6
    # Laikipia: P5  W0  D0  L5  GF119  GA152  GD-33  Pts0
    men_standings = [
        (sia_m, 4, 4, 0, 0, 135, 94),
        (mak_m, 5, 3, 0, 2, 117, 125),
        (lai_m, 5, 0, 0, 5, 119, 152),
    ]
    for team, played, won, drawn, lost, gf, ga in men_standings:
        pt, created = PoolTeam.objects.get_or_create(
            pool=men_pool, team=team,
        )
        pt.played = played
        pt.won = won
        pt.drawn = drawn
        pt.lost = lost
        pt.goals_for = gf
        pt.goals_against = ga
        pt.save()

    # Men fixtures (only create if none exist yet for this competition)
    if not Fixture.objects.filter(competition=men_comp).exists():
        men_fixtures = [
            # (home, away, h_score, a_score, date, time)
            (mak_m, lai_m, 23, 22, tue, "10:00"),   # Tue 14/4
            (mak_m, lai_m, 23, 22, wed, "08:00"),   # Wed 15/4
            (sia_m, mak_m, 29, 23, wed, "12:00"),   # Wed 15/4
            (lai_m, sia_m, 22, 35, thu, "10:00"),   # Thu 16/4
            (mak_m, sia_m, 20, 28, thu, "14:00"),   # Thu 16/4
            (lai_m, mak_m, 24, 28, fri, "09:00"),   # Fri 17/4
            (sia_m, lai_m, 43, 29, fri, "12:00"),   # Fri 17/4
        ]
        for home, away, hs, as_, dt, tm in men_fixtures:
            make_fixture(men_comp, men_pool, home, away, hs, as_, dt, tm)

    # ═══════════════════════════════════════════════════════════
    #  WOMEN'S HANDBALL
    # ═══════════════════════════════════════════════════════════
    women_comp, _ = Competition.objects.get_or_create(
        name="Handball (Women) — KYISA 2026",
        defaults={
            "sport_type": "handball_women",
            "gender": "women",
            "format_type": "group_stage",
            "season": "2026",
            "age_group": "U23",
            "status": "group_stage",
            "is_exhibition": True,
            "start_date": wed,
            "end_date": fri,
            "max_teams": 3,
            "teams_per_group": 3,
            "qualify_from_group": 1,
        },
    )
    if women_comp.status != "group_stage":
        women_comp.status = "group_stage"
        women_comp.format_type = "group_stage"
        women_comp.is_exhibition = True
        women_comp.save(update_fields=["status", "format_type", "is_exhibition"])

    mak_w = ensure_team(makueni_c, "handball_women", women_comp)
    lai_w = ensure_team(laikipia_c, "handball_women", women_comp)
    sia_w = ensure_team(siaya_c, "handball_women", women_comp)

    women_pool, _ = Pool.objects.get_or_create(
        competition=women_comp, name="Group A",
    )

    # Women standings (calculated from 6 results)
    # Siaya:    P4  W4  D0  L0  GF102  GA64   GD+38  Pts8
    # Makueni:  P4  W2  D0  L2  GF93   GA89   GD+4   Pts4
    # Laikipia: P4  W0  D0  L4  GF57   GA99   GD-42  Pts0
    women_standings = [
        (sia_w, 4, 4, 0, 0, 102, 64),
        (mak_w, 4, 2, 0, 2, 93, 89),
        (lai_w, 4, 0, 0, 4, 57, 99),
    ]
    for team, played, won, drawn, lost, gf, ga in women_standings:
        pt, created = PoolTeam.objects.get_or_create(
            pool=women_pool, team=team,
        )
        pt.played = played
        pt.won = won
        pt.drawn = drawn
        pt.lost = lost
        pt.goals_for = gf
        pt.goals_against = ga
        pt.save()

    # Women fixtures
    if not Fixture.objects.filter(competition=women_comp).exists():
        women_fixtures = [
            (mak_w, lai_w, 23, 14, wed, "10:00"),   # Wed 15/4
            (sia_w, mak_w, 26, 15, wed, "14:00"),   # Wed 15/4
            (sia_w, lai_w, 25, 14, wed, "16:00"),   # Wed 15/4
            (lai_w, sia_w, 11, 20, thu, "12:00"),   # Thu 16/4
            (mak_w, sia_w, 24, 31, fri, "10:30"),   # Fri 17/4
            (lai_w, mak_w, 18, 31, fri, "13:30"),   # Fri 17/4
        ]
        for home, away, hs, as_, dt, tm in women_fixtures:
            make_fixture(women_comp, women_pool, home, away, hs, as_, dt, tm)


def reverse_handball(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    Fixture = apps.get_model("competitions", "Fixture")
    PoolTeam = apps.get_model("competitions", "PoolTeam")
    Pool = apps.get_model("competitions", "Pool")

    for name in [
        "Handball (Men) — KYISA 2026",
        "Handball (Women) — KYISA 2026",
    ]:
        comp = Competition.objects.filter(name=name).first()
        if comp:
            Fixture.objects.filter(competition=comp).delete()
            PoolTeam.objects.filter(pool__competition=comp).delete()
            Pool.objects.filter(competition=comp).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0011_delete_tbd_fixtures"),
        ("teams", "0020_team_discipline"),
    ]
    operations = [
        migrations.RunPython(seed_handball, reverse_handball),
    ]
