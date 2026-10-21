"""
Teams app configuration.
"""
from django.apps import AppConfig


class TeamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teams'

    def ready(self):
        """Import signals when the app is ready."""
        import teams.signals
        self._ensure_iprs_columns()

    def _ensure_iprs_columns(self):
        """
        Add verifisha_* and prembly_* columns to teams_countyplayer if missing.
        Each column is added individually so a partial failure doesn't block others.
        """
        try:
            from django.db import connection

            columns_to_add = [
                ('verifisha_report_id',   "VARCHAR(255) NOT NULL DEFAULT ''"),
                ('verifisha_status',      "VARCHAR(20)  NOT NULL DEFAULT 'not_checked'"),
                ('verifisha_notes',       "TEXT         NOT NULL DEFAULT ''"),
                ('verifisha_checked_at',  "TIMESTAMPTZ"),
                ('prembly_status',        "VARCHAR(20)  NOT NULL DEFAULT 'not_checked'"),
                ('prembly_reference',     "VARCHAR(255) NOT NULL DEFAULT ''"),
                ('prembly_verified_name', "VARCHAR(200) NOT NULL DEFAULT ''"),
                ('prembly_notes',         "TEXT         NOT NULL DEFAULT ''"),
                ('prembly_checked_at',    "TIMESTAMPTZ"),
                ('is_age_eligible',       "BOOLEAN NOT NULL DEFAULT TRUE"),
            ]

            with connection.cursor() as cursor:
                # Drop stale columns from very early attempts
                for stale in ('huduma_reference', 'huduma_notes'):
                    try:
                        cursor.execute(
                            f"ALTER TABLE teams_countyplayer DROP COLUMN IF EXISTS {stale}"
                        )
                    except Exception:
                        pass

                for col, coldef in columns_to_add:
                    try:
                        cursor.execute("""
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='teams_countyplayer' AND column_name=%s
                        """, [col])
                        if not cursor.fetchone():
                            cursor.execute(
                                f"ALTER TABLE teams_countyplayer ADD COLUMN {col} {coldef}"
                            )
                    except Exception as exc:
                        import logging
                        logging.getLogger(__name__).warning(
                            'teams.apps: failed to add column %s: %s', col, exc
                        )

        except Exception:
            pass
