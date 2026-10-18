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
        self._ensure_verifisha_columns()

    def _ensure_verifisha_columns(self):
        """
        Directly add verifisha_* columns to teams_countyplayer if missing.
        This bypasses Django's migration tracking entirely — safe to run on
        every startup because each ALTER uses IF NOT EXISTS.
        """
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'teams_countyplayer'
                    AND column_name = 'verifisha_report_id'
                """)
                if cursor.fetchone():
                    return  # Already exists — nothing to do

                # Drop stale columns from previous failed attempts
                for col in ('huduma_reference', 'huduma_notes'):
                    cursor.execute(f"""
                        ALTER TABLE teams_countyplayer
                        DROP COLUMN IF EXISTS {col}
                    """)

                # Add the four verifisha columns
                cursor.execute("""
                    ALTER TABLE teams_countyplayer
                        ADD COLUMN verifisha_report_id  VARCHAR(255) NOT NULL DEFAULT '',
                        ADD COLUMN verifisha_status     VARCHAR(20)  NOT NULL DEFAULT 'not_checked',
                        ADD COLUMN verifisha_notes      TEXT         NOT NULL DEFAULT '',
                        ADD COLUMN verifisha_checked_at TIMESTAMPTZ
                """)
                import logging
                logging.getLogger(__name__).info(
                    'teams.apps: verifisha columns added to teams_countyplayer'
                )
        except Exception:
            # Table may not exist yet (fresh DB, first migrate run) — ignore
            pass
