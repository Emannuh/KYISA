"""
Database-portable helpers for the teams_countyplayer column migrations.

Migrations 0022–0027 were written as Postgres-only idempotent SQL
(``DO $$ … $$`` blocks and ``information_schema`` lookups) to recover from a
Railway deploy where migrations were recorded without their DDL running.

That SQL cannot run on SQLite (local development), so ``migrate`` failed there.
These helpers keep the Postgres path byte-for-byte identical and, on any other
backend, perform the same "add the column only if it's missing" logic using
Django's database introspection.

This module starts with an underscore, so Django's migration loader ignores it.
"""
from django.db import migrations

TABLE = 'teams_countyplayer'


def existing_columns(connection, table=TABLE):
    with connection.cursor() as cursor:
        return {col.name for col in connection.introspection.get_table_description(cursor, table)}


def ensure_columns(connection, columns, drop=(), table=TABLE):
    """Add each missing column (name -> SQL definition) and drop stale ones, idempotently."""
    present = existing_columns(connection, table)
    with connection.cursor() as cursor:
        for name in drop:
            if name in present:
                cursor.execute(f'ALTER TABLE {table} DROP COLUMN "{name}"')
        for name, definition in columns.items():
            if name not in present:
                cursor.execute(f'ALTER TABLE {table} ADD COLUMN "{name}" {definition}')


class PostgresSQLOrEnsureColumns(migrations.RunSQL):
    """
    RunSQL that executes its SQL on PostgreSQL only.

    On other backends it ensures ``columns`` exist (and ``drop`` columns don't)
    instead. Reversing on a non-Postgres backend is a no-op: it's local dev data.
    """

    def __init__(self, sql, reverse_sql=None, *, columns, drop=(), **kwargs):
        super().__init__(sql, reverse_sql=reverse_sql, **kwargs)
        self.columns = columns
        self.drop = tuple(drop)

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            return super().database_forwards(app_label, schema_editor, from_state, to_state)
        ensure_columns(schema_editor.connection, self.columns, self.drop)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == 'postgresql':
            return super().database_backwards(app_label, schema_editor, from_state, to_state)
