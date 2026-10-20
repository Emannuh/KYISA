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
        Directly add verifisha_* and prembly_* columns to teams_countyplayer if missing.
        Bypasses Django migration tracking — safe on every startup (checks first).
        """
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                def col_exists(col):
                    cursor.execute("""
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='teams_countyplayer' AND column_name=%s
                    """, [col])
                    return bool(cursor.fetchone())

                # Verifisha columns
                if not col_exists('verifisha_report_id'):
                    for stale in ('huduma_reference', 'huduma_notes'):
                        cursor.execute(f"ALTER TABLE teams_countyplayer DROP COLUMN IF EXISTS {stale}")
                    cursor.execute("""
                        ALTER TABLE teams_countyplayer
                            ADD COLUMN verifisha_report_id  VARCHAR(255) NOT NULL DEFAULT '',
                            ADD COLUMN verifisha_status     VARCHAR(20)  NOT NULL DEFAULT 'not_checked',
                            ADD COLUMN verifisha_notes      TEXT         NOT NULL DEFAULT '',
                            ADD COLUMN verifisha_checked_at TIMESTAMPTZ
                    """)

                # Prembly columns
                if not col_exists('prembly_status'):
                    cursor.execute("""
                        ALTER TABLE teams_countyplayer
                            ADD COLUMN prembly_status     VARCHAR(20)  NOT NULL DEFAULT 'not_checked',
                            ADD COLUMN prembly_reference  VARCHAR(255) NOT NULL DEFAULT '',
                            ADD COLUMN prembly_notes      TEXT         NOT NULL DEFAULT '',
                            ADD COLUMN prembly_checked_at TIMESTAMPTZ
                    """)

                import logging
                logging.getLogger(__name__).info('teams.apps: IPRS columns checked/added')
        except Exception:
            pass
