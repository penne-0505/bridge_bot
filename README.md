# Bridge Base

`bridge_bot` は Discord のチャンネル間でメッセージ・リアクションをミラーリングする最小構成です。Docker やホスティング先で Postgres を使い、環境変数経由で集中管理された永続化レイヤーを利用できます。

## 構成

- `app/` : 環境変数の読み込みと依存性注入。Supabase Python SDK のクライアントを構築し、Discord クライアントとストアを初期化します。
- `bot/` : `BridgeBotClient`、ブリッジコマンド、ChannelBridgeManager を含むロジック。
- `bot/bridge/` : プロフィール・メッセージストアとルートローダー。メタデータは PostgreSQL の `bridge_profiles` と `bridge_messages` に保存されます。
- `docs/` : 設定、運用手順、Postgres セットアップのガイド。
- `data/` : 起動前診断などで一時ファイルを書き込む作業ディレクトリ。

## 環境変数

| 変数名 | 説明 | 備考 |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot の Bot トークン。必須。 | - |
| `SUPABASE_URL` | Supabase プロジェクトの URL。例: `https://xxxx.supabase.co`。 | 起動時に未設定だとエラーになります。 |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase の service role key。 | 起動時に未設定だとエラーになります。 |
| `BRIDGE_ROUTES_ENABLED` | `true` で環境変数からルート定義を読み込み、メッセージブリッジ機能を有効化。`false` ならルートはロードされません。 | 既定値 `false`。 |
| `BRIDGE_ROUTES` | JSON 配列でルートを定義。`BRIDGE_ROUTES_ENABLED=true` で必須。 | - |
| `BRIDGE_ROUTES_REQUIRE_RECIPROCAL` | `true` のとき双方向ルートが必須。 | 既定値 `false`。 |
| `BRIDGE_ROUTES_STRICT` | `true` のとき不正なルートを検出すると起動を中断。 | 既定値 `false`。 |

詳細な環境変数の使い方は [docs/bridge_configuration.md](docs/bridge_configuration.md) を参照してください。

## データベース

Supabase の PostgreSQL 上で `bridge_profiles` / `bridge_messages` テーブルを管理し、サーバー間での運用監視性を高めます。テーブル作成手順は [docs/guide/postgresql_setup.md](docs/guide/postgresql_setup.md) にまとめています。起動前に SQL を適用してください。

## セットアップ

1. `poetry install` で依存関係をインストール。
2. Supabase プロジェクトを用意し、`SUPABASE_URL` と `SUPABASE_SERVICE_ROLE_KEY` を含む環境変数を設定する。`docs/guide/postgresql_setup.md` の SQL を Supabase SQL Editor で実行する。
3. `DISCORD_BOT_TOKEN` とブリッジルートの情報を環境変数で渡す。

## 実行方法

```bash
poetry run python main.py
```

ブリッジルートは `BRIDGE_ROUTES_ENABLED=true` と `BRIDGE_ROUTES='[...]'` の組み合わせでのみ読み込まれます。

## 起動前診断

`main.py` の起動時に、Bot が正しく動作できるか確認するセルフチェックが自動で実行されます。

- `DISCORD_BOT_TOKEN` と Supabase の接続情報の検出および接続性を検証します。
- `data/` ディレクトリの読み書き可否を確認します。
- ブリッジルートの設定（環境変数 `BRIDGE_ROUTES`）を検証し、問題があれば警告/エラーをログに出力します。

ログに `BridgeBot 起動前診断` という見出しが出力されるので、運用時は最初にこのブロックを確認することで環境状態を素早く把握できます。

## データディレクトリ

起動前診断では `data/` ディレクトリへの書き込み可否を確認します。運用で Supabase の `bridge_messages` テーブルに保存されているデータを調整したい場合は、`docs/bridge_message_store.md` に記載のスクリプトや SQL をお使いください。
