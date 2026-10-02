from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("matches", "0006_alter_squadsubmission_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="matchreport",
            name="stats_processed",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Set to True after pool standings and player statistics have been "
                    "updated for this report. Re-processing is blocked unless explicitly "
                    "reset (e.g. after a result override)."
                ),
            ),
        ),
    ]
