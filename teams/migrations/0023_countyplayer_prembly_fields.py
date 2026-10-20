"""
Migration 0023 — Add Prembly IPRS fields to CountyPlayer.
Uses DO $$ ... $$ idempotent SQL (same pattern as 0022).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0022_countyplayer_huduma_reference_huduma_notes_pending'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='prembly_status') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN prembly_status VARCHAR(20) NOT NULL DEFAULT 'not_checked';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='prembly_reference') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN prembly_reference VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='prembly_notes') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN prembly_notes TEXT NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='teams_countyplayer' AND column_name='prembly_checked_at') THEN
        ALTER TABLE teams_countyplayer ADD COLUMN prembly_checked_at TIMESTAMPTZ;
    END IF;
END $$;
            """,
            reverse_sql="""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='teams_countyplayer' AND column_name='prembly_status') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN prembly_status;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='teams_countyplayer' AND column_name='prembly_reference') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN prembly_reference;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='teams_countyplayer' AND column_name='prembly_notes') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN prembly_notes;
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='teams_countyplayer' AND column_name='prembly_checked_at') THEN
        ALTER TABLE teams_countyplayer DROP COLUMN prembly_checked_at;
    END IF;
END $$;
            """,
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_status',
                    field=models.CharField(
                        choices=[('not_checked','Not Checked'),('verified','Verified'),('failed','Failed')],
                        default='not_checked', max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_reference',
                    field=models.CharField(blank=True, default='', max_length=255),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_notes',
                    field=models.TextField(blank=True, default=''),
                ),
                migrations.AddField(
                    model_name='countyplayer',
                    name='prembly_checked_at',
                    field=models.DateTimeField(blank=True, null=True),
                ),
            ],
        ),
    ]
