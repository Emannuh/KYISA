from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0022_countyplayer_huduma_reference_huduma_notes_pending'),
    ]

    operations = [
        # Add ineligible choice to verification_status
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
        # Prembly verification fields
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
                help_text='Prembly Kenya IPRS verification result',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='prembly_reference',
            field=models.CharField(
                blank=True, default='',
                help_text='Prembly verification reference ID',
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='prembly_verified_name',
            field=models.CharField(
                blank=True, default='',
                help_text='Official name returned by Prembly IPRS',
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name='countyplayer',
            name='prembly_checked_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Age eligibility flag
        migrations.AddField(
            model_name='countyplayer',
            name='is_age_eligible',
            field=models.BooleanField(
                default=True,
                help_text='False if player age is outside 18-23 bracket at registration time',
            ),
        ),
    ]
