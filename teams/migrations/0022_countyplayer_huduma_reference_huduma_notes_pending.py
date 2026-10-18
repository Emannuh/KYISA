"""
Migration: add Verifisha fields to CountyPlayer.
Uses RunSQL with IF NOT EXISTS so it is safe to run even if columns
were partially created in a previous failed attempt.
Also reverts any accidental huduma_status 'pending' choice addition.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0021_alter_team_name_alter_team_unique_together'),
    ]

    operations = [
        # Safely add verifisha columns
        migrations.RunSQL(
            sql="""
                ALTER TABLE teams_countyplayer
                    ADD COLUMN IF NOT EXISTS verifisha_report_id VARCHAR(255) NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS verifisha_status    VARCHAR(20)  NOT NULL DEFAULT 'not_checked',
                    ADD COLUMN IF NOT EXISTS verifisha_notes     TEXT         NOT NULL DEFAULT '',
                    ADD COLUMN IF NOT EXISTS verifisha_checked_at TIMESTAMPTZ;
            """,
            reverse_sql="""
                ALTER TABLE teams_countyplayer
                    DROP COLUMN IF EXISTS verifisha_report_id,
                    DROP COLUMN IF EXISTS verifisha_status,
                    DROP COLUMN IF EXISTS verifisha_notes,
                    DROP COLUMN IF EXISTS verifisha_checked_at;
            """,
        ),
        # Also drop the accidental huduma_reference/huduma_notes columns
        # if they were partially added by any previous deploy attempt
        migrations.RunSQL(
            sql="""
                ALTER TABLE teams_countyplayer
                    DROP COLUMN IF EXISTS huduma_reference,
                    DROP COLUMN IF EXISTS huduma_notes;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Restore huduma_status to original 3 choices (remove accidental 'pending')
        migrations.AlterField(
            model_name='countyplayer',
            name='huduma_status',
            field=models.CharField(
                choices=[
                    ('not_checked', 'Not Checked'),
                    ('verified', 'Verified'),
                    ('failed', 'Failed'),
                ],
                default='not_checked',
                max_length=20,
            ),
        ),
        # Register the new verifisha fields with Django's migration state
        migrations.AddField(
            model_name='countyplayer',
            name='verifisha_report_id',
            field=models.CharField(blank=True, default='', max_length=255,
                                   help_text='Verifisha report ID returned from API'),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='verifisha_status',
            field=models.CharField(
                blank=True, default='not_checked', max_length=20,
                choices=[
                    ('not_checked', 'Not Checked'),
                    ('pending', 'Pending — awaiting webhook'),
                    ('verified', 'Verified'),
                    ('failed', 'Failed'),
                ],
                help_text='Verifisha IPRS verification status',
            ),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='verifisha_notes',
            field=models.TextField(blank=True, default='',
                                   help_text='Notes from Verifisha IPRS check'),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='verifisha_checked_at',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
