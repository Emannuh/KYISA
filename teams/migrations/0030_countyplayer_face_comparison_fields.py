"""
Migration: add face comparison fields to CountyPlayer
  - face_match_status       CharField  (not_checked / match / no_match / failed)
  - face_match_confidence   FloatField (0–100 similarity score)
  - face_match_checked_at   DateTimeField
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teams", "0029_merge_20261023_1617"),
    ]

    operations = [
        migrations.AddField(
            model_name="countyplayer",
            name="face_match_status",
            field=models.CharField(
                choices=[
                    ("not_checked", "Not Checked"),
                    ("match",       "Face Match"),
                    ("no_match",    "Face No Match"),
                    ("failed",      "Check Failed"),
                ],
                default="not_checked",
                help_text="Prembly face comparison result: submitted photo vs IPRS photo",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="countyplayer",
            name="face_match_confidence",
            field=models.FloatField(
                blank=True,
                null=True,
                help_text="Prembly face similarity score (0–100)",
            ),
        ),
        migrations.AddField(
            model_name="countyplayer",
            name="face_match_checked_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the face comparison was last run",
            ),
        ),
    ]
