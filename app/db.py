from __future__ import annotations

import logging

from supabase import Client, create_client

LOGGER = logging.getLogger(__name__)


def create_supabase_client(url: str, service_role_key: str) -> Client:
    """Create a shared Supabase client for the entire application."""
    LOGGER.info("Supabase client initialization: %s", url)
    return create_client(url, service_role_key)


__all__ = ["create_supabase_client"]
