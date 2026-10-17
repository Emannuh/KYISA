from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('admin_dashboard', '0005_activitylog_media_actions'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=100)),
                ('size', models.PositiveIntegerField(default=0, help_text='File size in bytes')),
                ('file', models.FileField(blank=True, upload_to='email_attachments/%Y/%m/')),
                ('email', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='attachments',
                    to='admin_dashboard.emaillog',
                )),
            ],
            options={
                'verbose_name': 'Email Attachment',
                'verbose_name_plural': 'Email Attachments',
                'ordering': ['filename'],
            },
        ),
    ]
