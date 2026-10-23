from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_logintoken'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('competition_manager', 'Organising Secretary'),
                    ('coordinator', 'Discipline Coordinator'),
                    ('soccer_coordinator', 'Soccer Coordinator'),
                    ('handball_coordinator', 'Handball Coordinator'),
                    ('basketball_coordinator', 'Basketball Coordinator'),
                    ('volleyball_coordinator', 'Volleyball Coordinator'),
                    ('verification_officer', 'Verification Officer'),
                    ('referee', 'Referee'),
                    ('team_manager', 'Team Manager'),
                    ('county_sports_admin', 'County Sports Director'),
                    ('cec_sports', 'County CEC Member - Sports'),
                    ('treasurer', 'Treasurer'),
                    ('jury_chair', 'Chair of the Jury'),
                    ('media_manager', 'Media Manager'),
                    ('secretary_general', 'Secretary General'),
                    ('scout', 'Scout'),
                    ('admin', 'System Admin'),
                    ('kicosca_officer', 'KICOSCA Sports Officer'),
                ],
                default='team_manager',
                max_length=30,
            ),
        ),
    ]
