"""
Management command: fix_migration_0022

Forces migration 0022 to re-apply by:
1. Checking if the verifisha columns are missing from the DB
2. If missing, deleting the stale django_migrations record
3. Running migrate which will then apply the migration properly

Usage: python manage.py fix_migration_0022
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix migration 0022 - adds missing verifisha columns to CountyPlayer'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if columns exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name='teams_countyplayer'
                AND column_name='verifisha_report_id'
            """)
            count = cursor.fetchone()[0]

            if count > 0:
                self.stdout.write(self.style.SUCCESS(
                    'verifisha columns already exist — no action needed.'
                ))
                return

            self.stdout.write('verifisha columns missing — applying fix...')

            # Delete stale migration record
            cursor.execute("""
                DELETE FROM django_migrations
                WHERE app='teams'
                AND name='0022_countyplayer_huduma_reference_huduma_notes_pending'
            """)
            self.stdout.write('Cleared stale migration record.')

        # Now run migrate
        from django.core.management import call_command
        call_command('migrate', 'teams', '0022', verbosity=2)
        self.stdout.write(self.style.SUCCESS('Migration 0022 applied successfully.'))
