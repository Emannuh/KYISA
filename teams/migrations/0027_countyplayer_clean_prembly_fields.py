"""
Migration 0027 — Sync Django state for prembly_notes, prembly_verified_name,
and remove the orphaned is_age_eligible BooleanField from the migration state
(the model now exposes this as a computed @property only).

The DB columns for prembly_notes and prembly_verified_name already exist
(added by apps.py _ensure_iprs_columns and migration 0026 respectively).
This migration only updates Django's internal migration state to match the
cleaned-up model — no DDL is run for these.

The is_age_eligible column is kept in the DB (it causes no harm and removing
it risks data loss if it was populated), but we remove it from Django's field
state so ORM queries no longer try to SELECT it.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0026_force_add_prembly_columns'),
    ]

    operations = [
        # ── Ensure prembly_notes column exists in DB ──────────────────────
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_notes'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_notes TEXT NOT NULL DEFAULT '';
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                      AND column_name = 'prembly_verified_name'
                ) THEN
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN prembly_verified_name VARCHAR(200) NOT NULL DEFAULT '';
                END IF;
            END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # ── Sync Django migration state ───────────────────────────────────
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                # Add prembly_notes to state (DB column added by RunSQL above)
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_notes',
                    field=models.TextField(blank=True, default='',
                                           help_text='Full Prembly response summary for audit trail'),
                ),
                # Add prembly_verified_name to state
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_verified_name',
                    field=models.CharField(blank=True, default='', max_length=200,
                                           help_text='Official name returned by Prembly IPRS'),
                ),
                # Update prembly_status choices to include mismatch
                migrations.AlterField(
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
                        help_text='Prembly Kenya IPRS verification result',
                        max_length=20,
                    ),
                ),
                # Remove is_age_eligible from Django state (now a @property only)
                migrations.RemoveField(
                    model_name='countyplayer',
                    name='is_age_eligible',
                ),
            ],
        ),
    ]
