"""
Migration 0025 — Guarantee prembly_* and is_age_eligible columns exist.

Previous migrations (0023, 0024) used IF NOT EXISTS SQL guards but were
recorded as applied on Railway without the DDL executing — a known issue
when a container exits mid-Procfile and Django retries on the next deploy.

This migration uses RunPython so it runs in-process Python, checks the
actual database schema (not Django's migration table), and adds only the
columns that are genuinely missing.  Safe to run multiple times.
"""
from django.db import migrations


def ensure_prembly_columns(apps, schema_editor):
    """Add missing prembly/age columns directly via cursor, checking first."""
    columns = {
        'prembly_status':      "VARCHAR(20)  NOT NULL DEFAULT 'not_checked'",
        'prembly_reference':   "VARCHAR(255) NOT NULL DEFAULT ''",
        'prembly_verified_name': "VARCHAR(200) NOT NULL DEFAULT ''",
        'prembly_checked_at':  "TIMESTAMP WITH TIME ZONE NULL",
        'is_age_eligible':     "BOOLEAN NOT NULL DEFAULT TRUE",
    }

    with schema_editor.connection.cursor() as cursor:
        # Fetch which columns already exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'teams_countyplayer'
              AND column_name = ANY(%s)
        """, [list(columns.keys())])
        existing = {row[0] for row in cursor.fetchall()}

        missing = {col: defn for col, defn in columns.items() if col not in existing}

        if not missing:
            return  # Nothing to do

        for col, defn in missing.items():
            cursor.execute(
                f'ALTER TABLE teams_countyplayer ADD COLUMN "{col}" {defn}'
            )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0024_fix_prembly_columns_direct_sql'),
    ]

    operations = [
        migrations.RunPython(ensure_prembly_columns, reverse_code=noop),
    ]
