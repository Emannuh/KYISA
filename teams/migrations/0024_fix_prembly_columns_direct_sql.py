"""
Migration 0024 — Ensure prembly columns exist (direct SQL, always runs).

This migration exists purely to guarantee the prembly_* and is_age_eligible
columns are present in the database, regardless of whether migration 0023
was recorded as applied without the SQL executing.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0023_countyplayer_prembly_fields_age_eligibility'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer'
                    AND column_name='prembly_status'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_status VARCHAR(20) NOT NULL DEFAULT 'not_checked',
                        ADD COLUMN prembly_reference VARCHAR(255) NOT NULL DEFAULT '',
                        ADD COLUMN prembly_verified_name VARCHAR(200) NOT NULL DEFAULT '',
                        ADD COLUMN prembly_checked_at TIMESTAMP WITH TIME ZONE NULL,
                        ADD COLUMN is_age_eligible BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
