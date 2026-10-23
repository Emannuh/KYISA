"""
Migration 0028 — Merge the two conflicting 0023 branches.

Two migrations were created with number 0023 on different machines:
  - 0023_countyplayer_prembly_fields
  - 0023_countyplayer_prembly_fields_age_eligibility

This merge migration makes them both parents of 0024, resolving the conflict.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0023_countyplayer_prembly_fields'),
        ('teams', '0023_countyplayer_prembly_fields_age_eligibility'),
    ]

    operations = [
    ]
