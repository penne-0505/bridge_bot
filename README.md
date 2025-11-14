# Bridge Base

`bridge_bot` は Discord のチャンネル間でメッセージ・リアクションをミラーリングする最小構成です。Docker やホスティング先で Postgres を使い、環境変数経由で集中管理された永続化レイヤーを利用できます。

## 構成

- `app/` : 環境変数の読み込みと依存性注入。`DATABASE_URL` から PostgreSQL 接続を構築し、Discord クライアントとストアを初期化します。
- `bot/` : `BridgeBotClient`、ブリッジコマンド、ChannelBridgeManager を含むロジック。
- `bot/bridge/` : プロフィール・メッセージストアとルートローダー。メタデータは PostgreSQL の `bridge_profiles` と `bridge_messages` に保存されます。
- `docs/` : 設定、運用手順、Postgres セットアップのガイド。
- `data/` : `channel_routes.json` をフォールバックして保存するディレクトリ。環境変数の `BRIDGE_ROUTES` が有効でないときのみ使用します。

## 環境変数

| 変数名 | 説明 | 備考 |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot の Bot トークン。必須。 | - |
| `DATABASE_URL` | Postgres 接続文字列。例: `postgresql://user:pass@db:5432/rin_bridge`。 | 起動時に未設定だとエラーになります。 |
| `BRIDGE_ROUTES_ENABLED` | `true` で環境変数からルート定義を読み込む。 | `false` または未設定であれば `data/channel_routes.json` が使われます。 |
| `BRIDGE_ROUTES` | JSON 配列でルートを定義。`BRIDGE_ROUTES_ENABLED=true` で必須。 | - |
| `BRIDGE_ROUTES_REQUIRE_RECIPROCAL` | `true` のとき双方向ルートが必須。 | 既定値 `false`。 |
| `BRIDGE_ROUTES_STRICT` | `true` のとき不正なルートを検出すると起動を中断。 | 既定値 `false`。 |

詳細な環境変数の使い方は [docs/bridge_configuration.md](docs/bridge_configuration.md) を参照してください。

## データベース

Postgres 上で `bridge_profiles` / `bridge_messages` テーブルを管理し、サーバー間での運用監視性を高めます。テーブルの作成や `DATABASE_URL` の準備手順は [docs/guide/postgresql_setup.md](docs/guide/postgresql_setup.md) にまとめています。起動時にテーブルがなければ自動生成されますが、手動でのセットアップや運用チェックも同ドキュメントをご利用ください。

## セットアップ

1. `poetry install` で依存関係をインストール。
2. Postgres を用意し、`DATABASE_URL` を含む環境変数を設定する。必要があれば `docs/guide/postgresql_setup.md` の SQL を `psql` で実行する。
3. `DISCORD_BOT_TOKEN` とブリッジルートの情報を環境変数で渡す（または `data/channel_routes.json` を用意）。

## 実行方法

```bash
poetry run python main.py
```

起動時に `BRIDGE_ROUTES_ENABLED=true` を設定していないと `data/channel_routes.json` がフォールバックで生成されます。

## データディレクトリ

`data/channel_routes.json` のみがこのリポジトリで生成されるため、ソース管理にも含めやすくなっています。運用で Postgres の `bridge_messages` テーブルに保存されているデータを調整したい場合は、`docs/bridge_message_store.md` に記載のスクリプトや SQL をお使いください。
