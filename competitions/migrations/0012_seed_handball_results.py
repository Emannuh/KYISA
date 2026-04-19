"""
Data migration — seed Handball (Men & Women) competitions, teams, pools,
standings, and completed fixtures from the 14-17 April 2026 results.

Teams: Makueni, Laikipia, Siaya (both genders)
Scoring: IHF standard — Win = 2 pts, Draw = 1, Loss = 0
"""
import datetime
from django.db import migrations


def seed_handball(apps, schema_editor):
    # Superseded by 0013 — no-op
    pass


def reverse_handball(apps, schema_editor):
    # Superseded by 0013 — no-op
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0011_delete_tbd_fixtures"),
        ("teams", "0020_team_discipline"),
    ]
    operations = [
        migrations.RunPython(seed_handball, reverse_handball),
    ]
