# チャンネルブリッジ設定ガイド

チャンネルブリッジ機能は、環境変数経由で有効化した場合のみルート定義をロードします。本番運用ではファイルをサーバーへ配布せずに安全に設定できるよう、以下の環境変数を用意しています。

## 必須環境変数

| 変数名 | 説明 | 例 |
| --- | --- | --- |
| `BRIDGE_ROUTES_ENABLED` | `true` に設定するとブリッジ機能が有効化され、`BRIDGE_ROUTES` からルートをロードします。`false` または未設定の場合はルートを一切ロードせず、ブリッジ機能が無効になります。 | `true` |
| `BRIDGE_ROUTES` | JSON 配列のルート定義。`BRIDGE_ROUTES_ENABLED=true` のとき必須です。 | `[{"src":{"guild":123,"channel":456},"dst":{"guild":789,"channel":101112}}]` |

| `DATABASE_URL` | Postgres 接続文字列。`bridge_profiles`/`bridge_messages` テーブルにアクセスするために必須です。 | `postgresql://user:pass@host:5432/rin_bridge` |

## 任意環境変数

| 変数名 | 説明 | 既定値 |
| --- | --- | --- |
| `BRIDGE_ROUTES_REQUIRE_RECIPROCAL` | `true` で双方向ルートの存在を検証します。片方向のみの定義が見つかると起動に失敗します。 | `false` |
| `BRIDGE_ROUTES_STRICT` | `true` で重複・形式不備・IDの不正を検出した瞬間に起動を中断します。`false` の場合は該当ルートのみ無視し、警告ログを残して起動を継続します。 | `false` |

## `DATABASE_URL` とテーブル

- `DATABASE_URL` は Postgres 接続文字列で、Bot 起動時に `bridge_profiles`/`bridge_messages` テーブルへアクセスするために必ず設定してください。接続先のテーブルが存在しない場合、`app/db.py` の `ensure_schema` が `CREATE TABLE IF NOT EXISTS` を実行します。
- 詳細なセットアップや手動の `psql` 操作は [docs/guide/postgresql_setup.md](docs/guide/postgresql_setup.md) を参照してください。

### JSON フォーマット

```json
[
  {
    "src": {"guild": 111111111111111111, "channel": 222222222222222222},
    "dst": {"guild": 333333333333333333, "channel": 444444444444444444}
  }
]
```

- `guild` / `channel` は Discord のスノーフレーク ID を整数で指定してください。
- `dst` へのルートは複数定義できます。同一ペアを複数回登録した場合は重複として扱われます。
- `BRIDGE_ROUTES_REQUIRE_RECIPROCAL=true` のときは、`src` と `dst` を入れ替えたもう一方のルートも必ず定義してください。

### 設定例 (fish shell)

```fish
set -x BRIDGE_ROUTES_ENABLED true
set -x BRIDGE_ROUTES '[{"src":{"guild":123,"channel":456},"dst":{"guild":789,"channel":101112}}]'
```

### フォールバックとローカル開発

JSON ファイルからの読み込みはサポートしていません。ローカル開発でも `BRIDGE_ROUTES_ENABLED=true` と `BRIDGE_ROUTES='[...]'` を必ず設定してください。

### エラー時の挙動

- JSON 解析エラーや正の整数でない ID、必須キー不足は `BRIDGE_ROUTES_STRICT` の値に応じて処理されます。
- `BRIDGE_ROUTES_REQUIRE_RECIPROCAL=true` が有効な状態で逆方向ルートが不足している場合は常にエラーになります。
- 起動ログに詳細な理由が記録されるので、CI/CD などで検証したい場合はログを確認してください。
