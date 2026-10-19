"""
Migration 0023 — Add Prembly verification fields and age eligibility to CountyPlayer.

Uses idempotent RunSQL with IF NOT EXISTS so it is safe to run multiple times
and will not fail if the column already exists or doesn't exist.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0022_countyplayer_huduma_reference_huduma_notes_pending'),
    ]

    operations = [
        # ── Use raw SQL so this is fully idempotent ──────────────────────────
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- Add prembly_status
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer' AND column_name='prembly_status'
                ) THEN
                    ALTER TABLE teams_countyplayer
                    ADD COLUMN prembly_status VARCHAR(20) NOT NULL DEFAULT 'not_checked';
                END IF;

                -- Add prembly_reference
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer' AND column_name='prembly_reference'
                ) THEN
                    ALTER TABLE teams_countyplayer
                    ADD COLUMN prembly_reference VARCHAR(255) NOT NULL DEFAULT '';
                END IF;

                -- Add prembly_verified_name
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer' AND column_name='prembly_verified_name'
                ) THEN
                    ALTER TABLE teams_countyplayer
                    ADD COLUMN prembly_verified_name VARCHAR(200) NOT NULL DEFAULT '';
                END IF;

                -- Add prembly_checked_at
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer' AND column_name='prembly_checked_at'
                ) THEN
                    ALTER TABLE teams_countyplayer
                    ADD COLUMN prembly_checked_at TIMESTAMP WITH TIME ZONE NULL;
                END IF;

                -- Add is_age_eligible
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='teams_countyplayer' AND column_name='is_age_eligible'
                ) THEN
                    ALTER TABLE teams_countyplayer
                    ADD COLUMN is_age_eligible BOOLEAN NOT NULL DEFAULT TRUE;
                END IF;

            END $$;
            """,
            reverse_sql="""
            DO $$
            BEGIN
                ALTER TABLE teams_countyplayer
                    DROP COLUMN IF EXISTS prembly_status,
                    DROP COLUMN IF EXISTS prembly_reference,
                    DROP COLUMN IF EXISTS prembly_verified_name,
                    DROP COLUMN IF EXISTS prembly_checked_at,
                    DROP COLUMN IF EXISTS is_age_eligible;
            END $$;
            """,
        ),

        # ── Update Django's migration state to match ─────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='countyplayer',
                    name='verification_status',
                    field=models.CharField(
                        choices=[
                            ('pending',    'Pending Verification'),
                            ('ineligible', 'Age Ineligible — Pending Review'),
                            ('verified',   'Verified / Approved'),
                            ('rejected',   'Rejected'),
                            ('resubmit',   'Requires Resubmission'),
                        ],
                        default='pending',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_status',
                    field=models.CharField(
                        choices=[
                            ('not_checked', 'Not Checked'),
                            ('verified',    'Verified'),
                            ('failed',      'Failed'),
                            ('mismatch',    'Name/DOB Mismatch'),
                        ],
                        default='not_checked',
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_reference',
                    field=models.CharField(blank=True, default='', max_length=255),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_verified_name',
                    field=models.CharField(blank=True, default='', max_length=200),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_checked_at',
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='is_age_eligible',
                    field=models.BooleanField(default=True),
                ),
            ],
        ),
    ]
