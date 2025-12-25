# Supabase PostgreSQL セットアップ

`bridge_bot` は Supabase Python SDK で `bridge_profiles` / `bridge_messages` テーブルを利用します。起動時の自動作成は行わないため、事前に Supabase SQL Editor でスキーマを作成してください。スキーマ定義は `supabase/bridge_schema.sql` にまとめています。

## 1. Supabase プロジェクトの用意

Supabase でプロジェクトを作成し、PostgreSQL データベースを用意します。

Supabase ダッシュボードから：

1. 新しいプロジェクトを作成
2. データベース設定から接続情報を取得
3. 必要に応じてデータベースのパスワードをリセット

Supabase は自動的にデータベースを用意するため、手動でのデータベース作成は不要です。

## 2. スキーマを作成する

以下の SQL を Supabase SQL Editor で実行すると、必要なテーブルとインデックスを作成できます。SQL は `supabase/bridge_schema.sql` と同一です。

```sql
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
```

## 3. Supabase 接続情報の設定

Supabase ダッシュボードからプロジェクト URL と service role key を取得し、環境変数にセットしてください。

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=ey...
```

## 4. 手動メンテナンスのヒント

- Supabase ダッシュボードの SQL Editor でテーブルの構造を確認: `select * from bridge_messages limit 1;`
- 古いメタデータを削除するには `docs/bridge_message_store.md` に記載のスクリプトを使うか、直接 `DELETE FROM bridge_messages WHERE updated_at < NOW() - INTERVAL '24 hours'` を実行してください。
- Supabase ダッシュボードの Database > Logs セクションでクエリの実行状況を監視できます。

このドキュメントは `docs/plan/postgresql_migration.md` にあるスキーマ案を踏まえて作成しており、今後の拡張でも同じ SQL をベースにできます。
