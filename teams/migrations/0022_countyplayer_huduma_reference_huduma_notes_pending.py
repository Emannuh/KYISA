"""
Cleanup migration — removes any partially-applied columns from failed
previous attempts. Uses IF EXISTS so it is always safe to run.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0021_alter_team_name_alter_team_unique_together'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE teams_countyplayer
                    DROP COLUMN IF EXISTS huduma_reference,
                    DROP COLUMN IF EXISTS huduma_notes,
                    DROP COLUMN IF EXISTS verifisha_report_id,
                    DROP COLUMN IF EXISTS verifisha_status,
                    DROP COLUMN IF EXISTS verifisha_notes,
                    DROP COLUMN IF EXISTS verifisha_checked_at;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
