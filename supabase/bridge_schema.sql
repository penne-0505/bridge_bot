CREATE TABLE IF NOT EXISTS bridge_profiles (
  id TEXT PRIMARY KEY,
  adjectives JSONB NOT NULL,
  nouns JSONB NOT NULL,
  guild_colors JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

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
);

CREATE INDEX IF NOT EXISTS bridge_messages_updated_at_idx ON bridge_messages (updated_at);
