from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_normalize_legacy_roles'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used', models.BooleanField(default=False)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='login_tokens',
                    to='accounts.user',
                )),
            ],
            options={
                'verbose_name': 'Login Token',
                'verbose_name_plural': 'Login Tokens',
            },
        ),
    ]
