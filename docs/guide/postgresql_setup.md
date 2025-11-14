# PostgreSQL セットアップ

`bridge_bot` は `DATABASE_URL` に設定した Postgres インスタンスと通信して `bridge_profiles` / `bridge_messages` テーブルを利用します。起動時にテーブルがなければ `app/db.py` 内の `ensure_schema` が `CREATE TABLE IF NOT EXISTS` を実行しますが、事前に手動でセットアップしたい場合は以下の手順を参考にしてください。

## 1. データベースの用意

運用環境で Postgres インスタンスを用意し、Bot 専用のユーザーとデータベースを作成してください。

```sql
CREATE ROLE bridge_user LOGIN PASSWORD 'secret';
CREATE DATABASE rin_bridge WITH OWNER bridge_user;
```

必要に応じてネットワークやファイアウォールを設定し、ZooKeeper などに `DATABASE_URL` を伝播させる準備を行います。

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

## 3. `DATABASE_URL` の設定

起動時は次のような接続文字列を環境変数 `DATABASE_URL` にセットしてください。

```
DATABASE_URL=postgresql://bridge_user:secret@db-host:5432/rin_bridge
```

必要に応じて SSL モード `sslmode=require` やタイムゾーンなどのクエリパラメータも付加できます。

## 4. 手動メンテナンスのヒント

- `psql` でテーブルの構造を確認: `psql "$DATABASE_URL" -c '\d bridge_messages'`
- 古いメタデータを削除するには `docs/bridge_message_store.md` に記載のスクリプトを使うか、直接 `DELETE FROM bridge_messages WHERE updated_at < NOW() - INTERVAL '24 hours'` を実行してください。
- Postgres 側で監視する場合は `bridge_messages_updated_at_idx` を使って `pg_stat_statements` などにアクセスすると purge の実行状況を追跡できます。

このドキュメントは `docs/plan/postgresql_migration.md` にあるスキーマ案を踏まえて作成しており、今後の拡張でも同じ SQL をベースにできます。
