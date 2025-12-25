# PostgreSQL移行計画

> 参考メモ: 現在の実装は Supabase Python SDK を利用し、接続は `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` に移行済み。DDL は `docs/guide/bridge_schema.sql` を使用する。

## 目的
TinyDB による JSON ストア（`bridge_profiles.json` / `bridge_messages.json`）は起動ディレクトリにローカルファイルを作るという目的には合致していますが、今後の運用や監視を考えると永続化レイヤーを Postgres に移行し、環境変数による集中管理と運用監視性を高めたいという要件に備えるための計画です。現状が非稼働状態であるため、過去データや運用ストップを気にせずゼロからスキーマを作り直します。

## 現状の TinyDB の責務（参考）
- `BridgeProfileStore`（`bot/bridge/profiles.py:63-112`）: `bridge_profiles` テーブルに `id: dictionary` レコードを 1 件用意し、`adjectives`/`nouns` のリストと `updated_at` を保持。`get_profile(seed=…)` でランダムな表示名・DiceBear シードを生成している。
- `BridgeMessageStore`（`bot/bridge/messages.py:72-160`）: `bridge_messages` テーブルに `source_id`・`destination_ids`・表示名/アバター URL・`dicebear_failed` フラグ・添付情報（`image_filename`/`notes`）・`updated_at` を記録し、`upsert`/`get`/`update_metadata`/`delete`/`purge_older_than` 等のメソッドで同期や purge に使われる。
- `app/container.py` で起動時に `TinyDB(data_dir / …)` でファイルを作成し、それぞれのストアに渡している。README や `docs/bridge_*` にも `data/` 以下への TinyDB 離散ファイルの生成を想定した記述がある。

## PostgreSQL スキーマ案

### `bridge_profiles` テーブル
| カラム名 | 型 | 備考 |
| --- | --- | --- |
| `id` | `TEXT` | 主キー。固定で `"dictionary"` を使うことで 1 レコードに限定。 |
| `adjectives` | `JSONB` | 形容詞リスト。`DEFAULT_ADJECTIVES` と同じ順で格納し、読み出し時に `json.dumps`/`json.loads` を使う。 |
| `nouns` | `JSONB` | 名詞リスト。 |
| `updated_at` | `TIMESTAMPTZ` | 辞書更新時刻。初期化時に `clock_timestamp()` などを入れる。 |

### `bridge_messages` テーブル
| カラム名 | 型 | 備考 |
| --- | --- | --- |
| `source_id` | `BIGINT` | 主キー。 |
| `destination_ids` | `JSONB` | `destination_ids` 配列（JSON list of ints）。挿入時に重複排除・ソートを行う。 |
| `profile_seed` | `TEXT` | DiceBear 用のシード。 |
| `display_name` | `TEXT` | 表示名。 |
| `avatar_url` | `TEXT` | アバター URL。 |
| `dicebear_failed` | `BOOLEAN` | DiceBear 呼び出し失敗フラグ。 |
| `image_filename` | `TEXT` | `BridgeMessageAttachmentMetadata.image_filename`。 |
| `attachment_notes` | `JSONB` | `notes` リスト。 |
| `updated_at` | `TIMESTAMPTZ` | 最終更新日時。`purge_older_than` 用にインデックスを張る。 |

### インデックス/制約
- `PRIMARY KEY (source_id)`（`bridge_messages`）
- `UNIQUE (id)`（`bridge_profiles` はテーブル設計上 implicit）
- `CREATE INDEX ON bridge_messages (updated_at)`（`purge_older_than` 対応）

## 実装ステップ
1. **依存関係と設定の整備**
   - `pyproject.toml` から `tinydb` を削除し、代わりに `psycopg[binary]`（または `psycopg_pool` と `psycopg`）を追加して PostgreSQL に接続できるようにする。将来的に SQLAlchemy を使う可能性を踏まえ、小規模なら `psycopg` 直書きでも十分。
   - `.env`/環境変数に `SUPABASE_URL` と `SUPABASE_SERVICE_ROLE_KEY` を追加し、`app/config.py` の `AppConfig` で読み込む。
   - `app/container.py` に PostgreSQL プール生成処理を追加し、起動時に 1 回ルートの `psycopg_pool.Pool`/`psycopg.Connection` を作成し、ストアインスタンスに渡す。

2. **PostgreSQL 接続ラッパーの実装**
   - 新規モジュール（例: `app/db.py`）で `psycopg_pool.Pool` を初期化し、`with pool.connection()` で `execute` を呼べるようなヘルパを提供。非同期イベントループでブロッキングを避けるため、必要に応じて `asyncio.to_thread` でラップするか、接続をシンプルに扱う。
   - `BridgeProfileStore`/`BridgeMessageStore` それぞれに「Postgres 版」を用意（`ProfileStore` だけ専用モジュールでも可）。旧 TinyDB クラスを残しておけば将来的にローカル保存オプションを付けられるが、ロード時は Postgres を使う。

3. **プロフィール辞書の Postgres 実装**
   - `BridgeProfileStore` の初期化で `SELECT adjectives, nouns FROM bridge_profiles WHERE id = 'dictionary'` を実行し、存在しなければ `INSERT` で `DEFAULT_ADJECTIVES`/`DEFAULT_NOUNS` を JSONB で格納。
   - `get_profile` は現在のローカル辞書キャッシュを使い、`BridgeProfile` の生成処理は現行と同じ。必要であれば `refresh_dictionary` を入れて明示的に再読込できるようにする。

4. **メッセージメタデータの Postgres 実装**
   - `upsert` は `INSERT ... ON CONFLICT (source_id) DO UPDATE SET ...` で `destination_ids`・`profile_seed` などを更新し、`updated_at` は `now()`。
   - `get` は `SELECT ...` で JSON を Python の `list[int]` に変換（`json.loads` 前に `record["destination_ids"]` など）。
   - `update_metadata` は `attachments` のみ更新し `updated_at` を `now()` に更新。
   - `remove_destination` は現行の `destination_ids` JSON を取得してフィルタ済みリストを `UPDATE`（空なら `DELETE`）。
   - `purge_older_than` は `DELETE FROM bridge_messages WHERE updated_at < %s` を実行。
   - レコード整合性はトランザクション(`with conn.transaction()`)を使って確保すると安全。

5. **起動・DI の組み込み**
   - `app/container.py` に `TinyDB` 生成をやめて、Postgres プールと `BridgeProfileStore`/`BridgeMessageStore` の Postgres 版インスタンスを `ChannelBridgeManager` に渡す。
   - 旧 `data/bridge_*.json` ファイルの生成は行わないが、README と `docs/bridge_*` に新 DB 前提の記述を加える。
   - 起動時に `bridge_messages` テーブルが空であれば問題なく `upsert` で生成される。表の初期作成は `docs/plan/` に `CREATE TABLE` スクリプトを添付するか、`psycopg` で `CREATE TABLE IF NOT EXISTS` を起動時に実行する。

6. **ドキュメント・運用の更新**
   - `README.md`/`docs/bridge_message_store.md`/`docs/bridge_draft.md` に Postgres の存在を反映し、`data/` に JSON ファイルを作らない旨や `docs/plan/` に接続設定手順を追加。
   - `docs/bridge_message_store.md` に「Postgres 上の `bridge_messages` テーブル」を対象にしたパージスクリプトや `psql` コマンド例を載せる。

## 検証・テスト
- Postgres ストア用に単体テストを追加（`psycopg` をモックして `Record` の変換ロジックを確認、`upsert`/`remove_destination` などの SQL を呼び出しているかを検証）。
- 既存の `tests/test_reaction_sync.py` をそのまま通すことで、DI された新ストアが `ChannelBridgeManager` と互換性を保てていることを担保（MagicMock spec に準拠している限り変更不要）。
- 実環境では公式 Postgres に接続できることを前提にして、`psql` で `CREATE TABLE` → Bot 起動 → `bridge_messages` への行挿入を確認する smoke test を行う。

## リスクと対策
- **ブロッキング**: 同期的な `psycopg` 呼び出しが Discord のイベントループを止める恐れがあるので、必要に応じて `asyncio.to_thread` で DB 操作をデスクローズするか、非同期ドライバ（`asyncpg`）への切り替えを検討する。
- **接続設定漏れ**: `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` が未設定だと起動しないため `AppConfig` の `load_config` で明示的なチェックとエラーメッセージを出す。
- **テーブル未作成**: `CREATE TABLE IF NOT EXISTS` をコンテナ起動時に行ったり、`docs/plan/postgresql_migration.md` のような SQL スクリプトを配布して手動実行することで対応。

## 次のステップ
1. `pyproject.toml` に Postgres 依存を追加し、`AppConfig` を拡張。
2. Postgres ストア実装と `app/container.py` の更新に着手。
3. テーブル作成 SQL と運用手順（`psql` 例など）を `docs/plan/` に補足し、README/他ドキュメントを更新。
