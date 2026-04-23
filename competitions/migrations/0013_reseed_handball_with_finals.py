"""
Data migration — Re-seed Handball (Men & Women) competitions with group
stage results AND finals.  Previous seed (0012) was lost because the
competitions were reset to registration status.

Men's Final:  Siaya 43–29 Makueni  (Fri 17 Apr)
Women's Final: Siaya 31–24 Makueni (Fri 17 Apr)

Teams: Makueni, Laikipia, Siaya (both genders)
Scoring: IHF standard — Win = 2 pts, Draw = 1, Loss = 0
"""
import datetime
from django.db import migrations


def seed_handball_with_finals(apps, schema_editor):
    Competition = apps.get_model("competitions", "Competition")
    Pool = apps.get_model("competitions", "Pool")
    PoolTeam = apps.get_model("competitions", "PoolTeam")
    Fixture = apps.get_model("competitions", "Fixture")
    Team = apps.get_model("teams", "Team")
    County = apps.get_model("teams", "County")

    # ── helpers ──────────────────────────────────────────────────
    def get_county(name):
        return County.objects.get(name=name)

    def ensure_team(county, sport_type, comp, suffix):
        # Historical databases may still enforce unique Team.name globally.
        # Use gendered names to avoid collisions across men's/women's teams.
        name = f"{county.name} {suffix}"
        team, _ = Team.objects.get_or_create(
            name=name,
            defaults={
                "county": county,
                "sport_type": sport_type,
                "competition": comp,
                "status": "registered",
                "payment_confirmed": True,
                "contact_phone": "+254700000000",
            },
        )
        if team.sport_type != sport_type:
            team.sport_type = sport_type
        if team.county_id != county.pk:
            team.county = county
        if team.competition_id != comp.pk:
            team.competition = comp
        team.save(update_fields=["sport_type", "county", "competition"])
        return team

    def make_fixture(comp, pool, home, away, h_score, a_score, date, time_str,
                     is_knockout=False, knockout_round="", winner=None):
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
            is_knockout=is_knockout,
            knockout_round=knockout_round,
            winner=winner,
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

    # ═══════════════════════════════════════════════════════════════
    #  MEN'S HANDBALL
    # ═══════════════════════════════════════════════════════════════
    men_comp = Competition.objects.filter(name="Handball (Men) — KYISA 2026").first()
    if not men_comp:
        return  # competition doesn't exist — skip

    men_comp.sport_type = "handball_men"
    men_comp.gender = "men"
    men_comp.format_type = "group_and_knockout"
    men_comp.season = "2026"
    men_comp.age_group = "U23"
    men_comp.status = "completed"
    men_comp.is_exhibition = True
    men_comp.start_date = tue
    men_comp.end_date = fri
    men_comp.max_teams = 3
    men_comp.teams_per_group = 3
    men_comp.qualify_from_group = 2
    men_comp.save()

    mak_m = ensure_team(makueni_c, "handball_men", men_comp, "HB Men")
    lai_m = ensure_team(laikipia_c, "handball_men", men_comp, "HB Men")
    sia_m = ensure_team(siaya_c, "handball_men", men_comp, "HB Men")

    # Pool
    men_pool, _ = Pool.objects.get_or_create(
        competition=men_comp, name="Group A",
    )

    # Men standings: Siaya 1st, Makueni 2nd, Laikipia 3rd
    men_standings = [
        (sia_m, 4, 4, 0, 0, 135, 94),
        (mak_m, 5, 3, 0, 2, 117, 125),
        (lai_m, 5, 0, 0, 5, 119, 152),
    ]
    for team, played, won, drawn, lost, gf, ga in men_standings:
        pt, _ = PoolTeam.objects.get_or_create(pool=men_pool, team=team)
        pt.played = played
        pt.won = won
        pt.drawn = drawn
        pt.lost = lost
        pt.goals_for = gf
        pt.goals_against = ga
        pt.save()

    # Men group fixtures + final
    if not Fixture.objects.filter(competition=men_comp).exists():
        # Group stage
        men_group = [
            (mak_m, lai_m, 23, 22, tue, "10:00"),
            (mak_m, lai_m, 23, 22, wed, "08:00"),
            (sia_m, mak_m, 29, 23, wed, "12:00"),
            (lai_m, sia_m, 22, 35, thu, "10:00"),
            (mak_m, sia_m, 20, 28, thu, "14:00"),
            (lai_m, mak_m, 24, 28, fri, "09:00"),
        ]
        for home, away, hs, as_, dt, tm in men_group:
            make_fixture(men_comp, men_pool, home, away, hs, as_, dt, tm)

        # ★ FINAL — Siaya vs Makueni
        make_fixture(
            men_comp, None, sia_m, mak_m, 43, 29, fri, "15:00",
            is_knockout=True, knockout_round="final", winner=sia_m,
        )

    # ═══════════════════════════════════════════════════════════════
    #  WOMEN'S HANDBALL
    # ═══════════════════════════════════════════════════════════════
    women_comp = Competition.objects.filter(name="Handball (Women) — KYISA 2026").first()
    if not women_comp:
        return

    women_comp.sport_type = "handball_women"
    women_comp.gender = "women"
    women_comp.format_type = "group_and_knockout"
    women_comp.season = "2026"
    women_comp.age_group = "U23"
    women_comp.status = "completed"
    women_comp.is_exhibition = True
    women_comp.start_date = wed
    women_comp.end_date = fri
    women_comp.max_teams = 3
    women_comp.teams_per_group = 3
    women_comp.qualify_from_group = 2
    women_comp.save()

    mak_w = ensure_team(makueni_c, "handball_women", women_comp, "HB Women")
    lai_w = ensure_team(laikipia_c, "handball_women", women_comp, "HB Women")
    sia_w = ensure_team(siaya_c, "handball_women", women_comp, "HB Women")

    women_pool, _ = Pool.objects.get_or_create(
        competition=women_comp, name="Group A",
    )

    # Women standings: Siaya 1st, Makueni 2nd, Laikipia 3rd
    women_standings = [
        (sia_w, 4, 4, 0, 0, 102, 64),
        (mak_w, 4, 2, 0, 2, 93, 89),
        (lai_w, 4, 0, 0, 4, 57, 99),
    ]
    for team, played, won, drawn, lost, gf, ga in women_standings:
        pt, _ = PoolTeam.objects.get_or_create(pool=women_pool, team=team)
        pt.played = played
        pt.won = won
        pt.drawn = drawn
        pt.lost = lost
        pt.goals_for = gf
        pt.goals_against = ga
        pt.save()

    # Women group fixtures + final
    if not Fixture.objects.filter(competition=women_comp).exists():
        women_group = [
            (mak_w, lai_w, 23, 14, wed, "10:00"),
            (sia_w, mak_w, 26, 15, wed, "14:00"),
            (sia_w, lai_w, 25, 14, wed, "16:00"),
            (lai_w, sia_w, 11, 20, thu, "12:00"),
            (mak_w, sia_w, 24, 31, fri, "10:30"),
            (lai_w, mak_w, 18, 31, fri, "13:30"),
        ]
        for home, away, hs, as_, dt, tm in women_group:
            make_fixture(women_comp, women_pool, home, away, hs, as_, dt, tm)

        # ★ FINAL — Siaya vs Makueni
        make_fixture(
            women_comp, None, sia_w, mak_w, 31, 24, fri, "16:00",
            is_knockout=True, knockout_round="final", winner=sia_w,
        )


def reverse_seed(apps, schema_editor):
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
            comp.status = "registration"
            comp.format_type = "group_and_knockout"
            comp.save()


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0012_seed_handball_results"),
        ("teams", "0020_team_discipline"),
    ]
    operations = [
        migrations.RunPython(seed_handball_with_finals, reverse_seed),
    ]
