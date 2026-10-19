"""
Migration 0025 — Guarantee prembly_* and is_age_eligible columns exist.

Migrations 0023 and 0024 used IF NOT EXISTS guards but were recorded as
applied on Railway without their DDL actually executing (a known issue when
a container exits mid-run and Django marks the migration done on retry).

This migration runs the same idempotent SQL under a new migration name that
Railway has never seen, so it will always execute on the next deploy.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0024_fix_prembly_columns_direct_sql'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_status'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_status VARCHAR(20) NOT NULL DEFAULT 'not_checked';
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_reference'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_reference VARCHAR(255) NOT NULL DEFAULT '';
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_verified_name'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_verified_name VARCHAR(200) NOT NULL DEFAULT '';
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_checked_at'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_checked_at TIMESTAMP WITH TIME ZONE NULL;
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'is_age_eligible'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN is_age_eligible BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
