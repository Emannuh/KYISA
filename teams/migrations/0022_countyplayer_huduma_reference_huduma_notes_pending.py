from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0021_alter_team_name_alter_team_unique_together'),
    ]

    operations = [
        # Add huduma_reference field to CountyPlayer
        migrations.AddField(
            model_name='countyplayer',
            name='huduma_reference',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Verifisha report ID or Huduma reference',
                max_length=255,
            ),
        ),
        # Add huduma_notes field to CountyPlayer
        migrations.AddField(
            model_name='countyplayer',
            name='huduma_notes',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Notes from IPRS/Verifisha verification',
            ),
        ),
        # Add 'pending' choice to huduma_status
        migrations.AlterField(
            model_name='countyplayer',
            name='huduma_status',
            field=models.CharField(
                choices=[
                    ('not_checked', 'Not Checked'),
                    ('verified', 'Verified'),
                    ('failed', 'Failed'),
                    ('pending', 'Pending'),
                ],
                default='not_checked',
                max_length=20,
            ),
        ),
    ]
