"""
Migration 0026 — Force-add prembly_* and is_age_eligible columns.

0023/0024/0025 were all recorded as applied by Railway without the DDL
running.  This migration uses RunPython with a live schema inspection so
it genuinely adds whatever columns are still missing, regardless of what
Django's django_migrations table says.
"""
from django.db import migrations


def force_add_columns(apps, schema_editor):
    columns = {
        'prembly_status':        "VARCHAR(20)  NOT NULL DEFAULT 'not_checked'",
        'prembly_reference':     "VARCHAR(255) NOT NULL DEFAULT ''",
        'prembly_verified_name': "VARCHAR(200) NOT NULL DEFAULT ''",
        'prembly_checked_at':    "TIMESTAMP WITH TIME ZONE NULL",
        'is_age_eligible':       "BOOLEAN NOT NULL DEFAULT TRUE",
    }

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'teams_countyplayer'
              AND column_name = ANY(%s)
        """, [list(columns.keys())])
        existing = {row[0] for row in cursor.fetchall()}

        for col, defn in columns.items():
            if col not in existing:
                cursor.execute(
                    f'ALTER TABLE teams_countyplayer ADD COLUMN "{col}" {defn}'
                )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0025_ensure_prembly_and_age_columns'),
    ]

    operations = [
        migrations.RunPython(force_add_columns, reverse_code=noop),
    ]
