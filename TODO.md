# TODO

## Supabase Python SDK migration
- [x] Replace psycopg/ConnectionPool usage with Supabase Python SDK client for `bridge_profiles` and `bridge_messages` operations.
- [x] Decide which Supabase auth credentials to use (service role key vs anon key) and how they are provided via env vars.
- [x] Update configuration and diagnostics to validate new Supabase env vars (dropping `SUPABASE_DB_URL`).
- [x] Align docs: `README.md`, `docs/bridge_configuration.md`, `docs/guide/postgresql_setup.md`, `docs/bridge_message_store.md`.
- [ ] Add/update tests or smoke-check guidance for Supabase connectivity.

## Guild color assignment (bridge embed)
- [ ] Confirm desired behavior: embed color based on source guild; assign color at startup for guilds missing a color.
- [ ] Extend Supabase schema to persist guild colors (likely new table or new columns in `bridge_profiles`).
- [ ] Implement color assignment with a palette that keeps perceptual distance between colors.
- [ ] Apply the guild color when building mirror embeds in `bot/bridge/manager.py`.
- [ ] Update docs + `supabase/bridge_schema.sql` + `docs/guide/postgresql_setup.md` to reflect schema change.
- [ ] Add operational guidance for updating guild color records (SQL snippet or helper).

## References
- `README.md` (Supabase SDK usage + setup)
- `docs/bridge_configuration.md` (Supabase URL/service role key requirements)
- `docs/guide/postgresql_setup.md` (schema setup flow)
- `app/db.py` (Supabase client creation)
- `bot/bridge/messages.py`, `bot/bridge/profiles.py` (storage access)
 - `supabase/bridge_schema.sql` (DDL source)
 - `bot/bridge/manager.py` (embed build path)
