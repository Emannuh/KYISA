from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import accounts.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('teams', '0023_countyplayer_prembly_fields_age_eligibility'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='KicoscaEdition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('year', models.PositiveIntegerField()),
                ('host_county', models.CharField(choices=[('Mombasa', 'Mombasa'), ('Nairobi', 'Nairobi'), ('Makueni', 'Makueni')], max_length=100)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-year']},
        ),
        migrations.CreateModel(
            name='KicoscaCountyEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('edition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='county_entries', to='kicosca.kicoscaedition')),
                ('county_registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kicosca_entries', to='teams.countyregistration')),
            ],
            options={'ordering': ['county_registration__county'], 'unique_together': {('edition', 'county_registration')}},
        ),
        migrations.CreateModel(
            name='KicoscaDiscipline',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sport', models.CharField(choices=[('football_men', 'Football (Men)'), ('football_women', 'Football (Women)'), ('volleyball_men', 'Volleyball (Men)'), ('volleyball_women', 'Volleyball (Women)'), ('basketball_men', 'Basketball (Men)'), ('basketball_women', 'Basketball (Women)'), ('handball_men', 'Handball (Men)'), ('handball_women', 'Handball (Women)'), ('athletics', 'Athletics'), ('swimming', 'Swimming'), ('rugby_sevens', 'Rugby Sevens (Men)'), ('netball', 'Netball (Women)')], max_length=30)),
                ('entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='disciplines', to='kicosca.kicoscacountyentry')),
            ],
            options={'ordering': ['sport'], 'unique_together': {('entry', 'sport')}},
        ),
        migrations.CreateModel(
            name='KicoscaPlayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('date_of_birth', models.DateField()),
                ('national_id_number', models.CharField(max_length=20)),
                ('kra_pin', models.CharField(blank=True, default='', max_length=11)),
                ('phone', models.CharField(max_length=13, validators=[accounts.models.kenya_phone_validator])),
                ('department', models.CharField(blank=True, default='', max_length=200)),
                ('employee_number', models.CharField(blank=True, default='', max_length=50)),
                ('position_title', models.CharField(blank=True, default='', max_length=100)),
                ('jersey_number', models.PositiveIntegerField(blank=True, null=True)),
                ('sport_position', models.CharField(blank=True, default='', max_length=50)),
                ('photo', models.ImageField(blank=True, null=True, upload_to='kicosca/photos/')),
                ('id_document', models.ImageField(blank=True, null=True, upload_to='kicosca/ids/')),
                ('payslip', models.FileField(blank=True, null=True, upload_to='kicosca/payslips/')),
                ('appointment_letter', models.FileField(blank=True, null=True, upload_to='kicosca/letters/')),
                ('iprs_photo', models.ImageField(blank=True, null=True, upload_to='kicosca/iprs_photos/')),
                ('prembly_status', models.CharField(choices=[('not_checked', 'Not Checked'), ('verified', 'Verified — County Employee'), ('failed', 'Failed — Not Found'), ('mismatch', 'Mismatch — Employer Differs'), ('pending', 'Pending Manual Review')], default='not_checked', max_length=20)),
                ('prembly_verified_name', models.CharField(blank=True, default='', max_length=200)),
                ('prembly_reference', models.CharField(blank=True, default='', max_length=255)),
                ('prembly_checked_at', models.DateTimeField(blank=True, null=True)),
                ('kra_employment_status', models.CharField(choices=[('not_checked', 'Not Checked'), ('verified', 'Verified — County Employee'), ('failed', 'Failed — Not Found'), ('mismatch', 'Mismatch — Employer Differs'), ('pending', 'Pending Manual Review')], default='not_checked', max_length=20)),
                ('kra_employer_name', models.CharField(blank=True, default='', max_length=300)),
                ('kra_employer_pin', models.CharField(blank=True, default='', max_length=20)),
                ('kra_verification_ref', models.CharField(blank=True, default='', max_length=255)),
                ('kra_checked_at', models.DateTimeField(blank=True, null=True)),
                ('kra_raw_response', models.JSONField(blank=True, default=dict)),
                ('verification_status', models.CharField(choices=[('pending', 'Pending Verification'), ('verified', 'Verified — Eligible'), ('rejected', 'Rejected — Ineligible'), ('resubmit', 'Requires Resubmission')], default='pending', max_length=20)),
                ('rejection_reason', models.TextField(blank=True, default='')),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('registered_at', models.DateTimeField(auto_now_add=True)),
                ('discipline', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='players', to='kicosca.kicoscadiscipline')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='kicosca_verified_players', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['last_name', 'first_name'], 'unique_together': {('discipline', 'national_id_number')}},
        ),
    ]
