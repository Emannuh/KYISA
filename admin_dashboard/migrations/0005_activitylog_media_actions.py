from django.db import migrations, models


def fix_media_manager_activity_logs(apps, schema_editor):
    ActivityLog = apps.get_model('admin_dashboard', 'ActivityLog')
    User = apps.get_model('accounts', 'User')

    media_manager_ids = list(
        User.objects.filter(role='media_manager').values_list('id', flat=True)
    )
    if not media_manager_ids:
        return

    generic_player_updates = ActivityLog.objects.filter(
        user_id__in=media_manager_ids,
        action='PLAYER_UPDATE',
        description__icontains='updated player information',
    )

    for log in generic_player_updates.select_related('user').iterator():
        first_name = (log.user.first_name or '').strip() if log.user else ''
        last_name = (log.user.last_name or '').strip() if log.user else ''
        full_name = f'{first_name} {last_name}'.strip()
        user_name = full_name or (log.user.email if log.user else 'A media manager')
        log.action = 'MEDIA_UPDATE'
        log.description = f'{user_name} updated media content'
        log.save(update_fields=['action', 'description'])

    for log in ActivityLog.objects.filter(
        user_id__in=media_manager_ids,
        action='PLAYER_CREATE',
        description__icontains='added a new player',
    ).select_related('user').iterator():
        first_name = (log.user.first_name or '').strip() if log.user else ''
        last_name = (log.user.last_name or '').strip() if log.user else ''
        full_name = f'{first_name} {last_name}'.strip()
        user_name = full_name or (log.user.email if log.user else 'A media manager')
        log.action = 'MEDIA_CREATE'
        log.description = f'{user_name} created media content'
        log.save(update_fields=['action', 'description'])

    for log in ActivityLog.objects.filter(
        user_id__in=media_manager_ids,
        action='PLAYER_DELETE',
        description__icontains='deleted a player',
    ).select_related('user').iterator():
        first_name = (log.user.first_name or '').strip() if log.user else ''
        last_name = (log.user.last_name or '').strip() if log.user else ''
        full_name = f'{first_name} {last_name}'.strip()
        user_name = full_name or (log.user.email if log.user else 'A media manager')
        log.action = 'MEDIA_DELETE'
        log.description = f'{user_name} deleted media content'
        log.save(update_fields=['action', 'description'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_user_assigned_discipline_alter_user_role'),
        ('admin_dashboard', '0004_alter_activitylog_action_emaillog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activitylog',
            name='action',
            field=models.CharField(
                choices=[
                    ('LOGIN', 'Login'),
                    ('LOGOUT', 'Logout'),
                    ('PASSWORD_CHANGE', 'Password Change'),
                    ('TEAM_CREATE', 'Team Created'),
                    ('TEAM_UPDATE', 'Team Updated'),
                    ('TEAM_DELETE', 'Team Deleted'),
                    ('TEAM_APPROVE', 'Team Approved'),
                    ('TEAM_REJECT', 'Team Rejected'),
                    ('TEAM_SUSPEND', 'Team Suspended'),
                    ('PLAYER_CREATE', 'Player Created'),
                    ('PLAYER_UPDATE', 'Player Updated'),
                    ('PLAYER_DELETE', 'Player Deleted'),
                    ('PLAYER_TRANSFER', 'Player Transfer'),
                    ('MATCH_CREATE', 'Match Created'),
                    ('MATCH_UPDATE', 'Match Updated'),
                    ('MATCH_DELETE', 'Match Deleted'),
                    ('MATCH_RESCHEDULE', 'Match Rescheduled'),
                    ('MATCH_REPORT', 'Match Report Submitted'),
                    ('MATCH_REPORT_APPROVE', 'Match Report Approved'),
                    ('RESULT_OVERRIDE', 'Result Override'),
                    ('STANDINGS_OVERRIDE', 'Standings Override'),
                    ('SG_OVERRIDE_ACK', 'SG Override Acknowledged'),
                    ('SG_OVERRIDE_REJECT', 'SG Override Rejected'),
                    ('FIXTURE_GENERATE', 'Fixtures Generated'),
                    ('FIXTURE_REGENERATE', 'Fixtures Regenerated'),
                    ('ZONE_ASSIGN', 'Zone Assigned'),
                    ('ZONE_UPDATE', 'Zone Updated'),
                    ('PAYMENT_RECEIVED', 'Payment Received'),
                    ('PAYMENT_VERIFIED', 'Payment Verified'),
                    ('SUSPENSION_CREATE', 'Suspension Created'),
                    ('SUSPENSION_LIFT', 'Suspension Lifted'),
                    ('MATCHDAY_SQUAD_SUBMIT', 'Matchday Squad Submitted'),
                    ('SQUAD_APPROVE', 'Squad Approved'),
                    ('SQUAD_REJECT', 'Squad Rejected'),
                    ('REFEREE_REGISTER', 'Referee Registered'),
                    ('REFEREE_APPROVE', 'Referee Approved'),
                    ('REFEREE_ACTION', 'Referee Action'),
                    ('MEDIA_CREATE', 'Media Created'),
                    ('MEDIA_UPDATE', 'Media Updated'),
                    ('MEDIA_DELETE', 'Media Deleted'),
                    ('USER_CREATE', 'User Created'),
                    ('USER_UPDATE', 'User Updated'),
                    ('USER_DELETE', 'User Deleted'),
                    ('USER_ROLE_CHANGE', 'User Role Changed'),
                    ('CONFIG_CHANGE', 'Configuration Changed'),
                    ('REGISTRATION_TOGGLE', 'Registration Window Toggled'),
                    ('ADMIN_ACTION', 'Admin Action'),
                    ('PAYMENT_ACTION', 'Payment Action'),
                    ('OTHER', 'Other Action'),
                ],
                max_length=50,
            ),
        ),
        migrations.RunPython(fix_media_manager_activity_logs, migrations.RunPython.noop),
    ]