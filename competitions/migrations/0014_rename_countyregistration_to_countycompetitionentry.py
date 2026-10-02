"""
Rename competitions.CountyRegistration → CountyCompetitionEntry.

Rationale: teams.CountyRegistration is the county sports admin onboarding
model (one per county, payment-driven). competitions.CountyRegistration tracks
a county's entry into a specific competition. The name collision caused
maintenance hazards and confusing cross-app imports.

The DB table is renamed from competitions_countyregistration →
competitions_countycompetitionentry. The alias
    CountyRegistration = CountyCompetitionEntry
in models.py keeps existing call sites working during the transition.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("competitions", "0013_reseed_handball_with_finals"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="CountyRegistration",
            new_name="CountyCompetitionEntry",
        ),
    ]
