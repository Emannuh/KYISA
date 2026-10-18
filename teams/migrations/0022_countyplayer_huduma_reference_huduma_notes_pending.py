"""
Migration 0022 — Add Verifisha fields to CountyPlayer.

Uses pure RunSQL with DO $$ ... $$ blocks so it is completely idempotent:
- drops any stale columns from previous failed attempts
- adds the four verifisha_* columns only if they don't already exist
- registers them in Django's migration state via SeparateDatabaseAndState

This approach bypasses the Django migration-state cache issue where the
migration was recorded as applied before the SQL actually ran.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0021_alter_team_name_alter_team_unique_together'),
    ]

    operations = [
        # Step 1: Clean up any stale columns AND add the new ones — all idempotent
        migrations.RunSQL(
            sql="""
DO $$
BEGIN
    -- Drop stale columns from previous failed attempts
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='huduma_reference') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN huduma_reference;
    END IF;

    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='huduma_notes') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN huduma_notes;
    END IF;

    -- Add verifisha_report_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='verifisha_report_id') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN verifisha_report_id VARCHAR(255) NOT NULL DEFAULT '';
    END IF;

    -- Add verifisha_status
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='verifisha_status') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN verifisha_status VARCHAR(20) NOT NULL DEFAULT 'not_checked';
    END IF;

    -- Add verifisha_notes
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='verifisha_notes') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN verifisha_notes TEXT NOT NULL DEFAULT '';
    END IF;

    -- Add verifisha_checked_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='verifisha_checked_at') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN verifisha_checked_at TIMESTAMPTZ;
    END IF;
END $$;
            """,
            reverse_sql="""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='verifisha_report_id') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN verifisha_report_id;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='verifisha_status') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN verifisha_status;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='verifisha_notes') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN verifisha_notes;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_name='teams_countyplayer' AND column_name='verifisha_checked_at') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN verifisha_checked_at;
    END IF;
END $$;
            """,
        ),

        # Step 2: Sync Django's migration state (no DB ops — just state)
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # DB already done above
            state_operations=[
                migrations.AddField(
                    model_name='countyplayer',
                    name='verifisha_report_id',
                    field=models.CharField(blank=True, default='', max_length=255),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='verifisha_status',
                    field=models.CharField(
                        choices=[('not_checked','Not Checked'),('pending','Pending'),
                                 ('verified','Verified'),('failed','Failed')],
                        default='not_checked', max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='verifisha_notes',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='verifisha_checked_at',
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        ),
    ]
