# Supabase PostgreSQL セットアップ

`bridge_bot` は `SUPABASE_DB_URL` に設定した Supabase PostgreSQL インスタンスと通信して `bridge_profiles` / `bridge_messages` テーブルを利用します。起動時にテーブルがなければ `app/db.py` 内の `ensure_schema` が `CREATE TABLE IF NOT EXISTS` を実行しますが、事前に手動でセットアップしたい場合は以下の手順を参考にしてください。

## 1. Supabase プロジェクトの用意

Supabase でプロジェクトを作成し、PostgreSQL データベースを用意します。

Supabase ダッシュボードから：
1. 新しいプロジェクトを作成
2. データベース設定から接続情報を取得
3. 必要に応じてデータベースのパスワードをリセット

Supabase は自動的にデータベースを用意するため、手動でのデータベース作成は不要です。

## 2. スキーマを作成する

以下の SQL を `psql` や管理ツールで実行すると、必要なテーブルとインデックスを作成できます。`app/db.py` のスキーマ案と同期しているため、起動直後に自動的に作成される場合は無理に実行する必要はありません。

```sql
CREATE TABLE IF NOT EXISTS bridge_profiles (
  id TEXT PRIMARY KEY,
  adjectives JSONB NOT NULL,
  nouns JSONB NOT NULL,
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

## 3. `SUPABASE_DB_URL` の設定

Supabase ダッシュボードの Settings > Database から PostgreSQL 接続文字列を取得し、環境変数 `SUPABASE_DB_URL` にセットしてください。

```
SUPABASE_DB_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
```

Supabase では接続プーリングを利用することを推奨します。Transaction モードまたは Session モードの接続文字列を使用してください。

## 4. 手動メンテナンスのヒント

- Supabase ダッシュボードの SQL Editor または `psql` でテーブルの構造を確認: `psql "$SUPABASE_DB_URL" -c '\d bridge_messages'`
- 古いメタデータを削除するには `docs/bridge_message_store.md` に記載のスクリプトを使うか、直接 `DELETE FROM bridge_messages WHERE updated_at < NOW() - INTERVAL '24 hours'` を実行してください。
- Supabase ダッシュボードの Database > Logs セクションでクエリの実行状況を監視できます。

このドキュメントは `docs/plan/postgresql_migration.md` にあるスキーマ案を踏まえて作成しており、今後の拡張でも同じ SQL をベースにできます。
