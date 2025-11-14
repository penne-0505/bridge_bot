from __future__ import annotations

import logging

from psycopg_pool import ConnectionPool

LOGGER = logging.getLogger(__name__)


def create_connection_pool(database_url: str) -> ConnectionPool:
    """Create a shared ConnectionPool for the entire application."""
    LOGGER.info("PostgreSQL connection pool initialization: %s", database_url)
    return ConnectionPool(conninfo=database_url)


def ensure_schema(pool: ConnectionPool) -> None:
    """Ensure the required tables and indexes exist."""  # noqa: D401
    profile_table_sql = """
    CREATE TABLE IF NOT EXISTS bridge_profiles (
        id TEXT PRIMARY KEY,
        adjectives JSONB NOT NULL,
        nouns JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
    )
    """
    message_table_sql = """
    CREATE TABLE IF NOT EXISTS bridge_messages (
        source_id BIGINT PRIMARY KEY,
        destination_ids JSONB NOT NULL,
        profile_seed TEXT NOT NULL,
        display_name TEXT NOT NULL,
        avatar_url TEXT NOT NULL,
        dicebear_failed BOOLEAN NOT NULL,
        image_filename TEXT,
        attachment_notes JSONB NOT NULL DEFAULT '[]'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
    )
    """
    index_sql = "CREATE INDEX IF NOT EXISTS bridge_messages_updated_at_idx ON bridge_messages (updated_at)"

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(profile_table_sql)
            cur.execute(message_table_sql)
            cur.execute(index_sql)
    LOGGER.info("PostgreSQL schema ensured.")
