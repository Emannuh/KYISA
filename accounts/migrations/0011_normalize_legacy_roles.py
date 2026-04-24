from django.db import migrations


def forwards(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='referee_manager').update(role='coordinator')


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_user_assigned_discipline_alter_user_role'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
