# ブリッジメッセージ記録のメンテナンス

`ChannelBridgeManager` は Discord 上で処理した表示名・アイコン URL・DiceBear 失敗フラグ・送信先メッセージ ID・添付ファイル情報を Supabase PostgreSQL の `bridge_messages` テーブルに保存します。編集同期やリアクション処理ではこのメタデータを参照し直すため、定期的なクリーンアップを推奨します。

## 古いレコードを定期削除する

24 時間を超えて編集される可能性が低いため、cron などから次のスクリプトを実行して古いレコードを削除してください。`SUPABASE_DB_URL` を環境変数で渡すと、Bot 起動時と同じ接続先にアクセスできます。

```bash
python - <<'PY'
import os
from datetime import datetime, timedelta, timezone

from psycopg_pool import ConnectionPool

database_url = os.environ["SUPABASE_DB_URL"]
threshold = datetime.now(timezone.utc) - timedelta(hours=24)

with ConnectionPool(conninfo=database_url) as pool:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM bridge_messages WHERE updated_at < %s",
                (threshold,),
            )
            print(f"Removed {cur.rowcount} expired bridge message records.")
PY
```

保持期間を変更したい場合は `timedelta` を調整してください。削除後は `ChannelBridgeManager` が新しいメタデータを再作成するため、再起動は不要です。

## ルート設定変更時のコード再同期

ルート定義（`BRIDGE_ROUTES` 環境変数で渡す JSON）を更新したときは、対象の `source_id` レコードを削除することで再同期できます。影響範囲を掴みにくい場合は、`bridge_messages` テーブルをまるごと空にしても問題ありません。Supabase から削除するには Supabase ダッシュボードの SQL Editor または `psql` で実行できます。

```bash
psql "$SUPABASE_DB_URL" -c "DELETE FROM bridge_messages WHERE TRUE;"
```

再同期後は、対象メッセージを再送信または編集することで新しいルートに沿ったメタデータが作成されます。必要なら `docs/guide/postgresql_setup.md` を参照し、Supabase PostgreSQL 側のテーブル定義も確認してください。
