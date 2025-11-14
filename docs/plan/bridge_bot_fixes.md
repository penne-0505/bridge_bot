# Bridge Bot 改善計画

## 背景
- `poetry run general-py-discord-bot` が `app.runtime` を参照しているが、対象モジュールが存在しないため起動できない。
- Poetry の package 設定が `src/` 配下を前提にしており、実際のコードがビルド成果物に含まれない。
- リアクション同期は 1 つの Bot リアクションで全ユーザーのリアクションを表現しているため、誰かがリアクションを外すと他ユーザー分まで消えてしまう。

## ゴール
1. 実際のエントリポイントを指すよう CLI 設定を修正し、`poetry run general-py-discord-bot` で Bot が起動できる状態にする。
2. 現行のディレクトリ構成（`app/`, `bot/` などがリポジトリ直下にある）と一致するよう Poetry パッケージ設定を見直す。
3. リアクション同期がユーザーごとの状態を保てるようにし、源メッセージにリアクションが残っている限りミラー先にも残る挙動にする。

## アプローチ
### 1. エントリポイント修正
- `pyproject.toml` の `[project.scripts]` を `main:main` など既存のエントリに変更。
- 変更後、`python main.py` を直接実行して動作確認。

### 2. Poetry パッケージ設定
- `[tool.poetry].packages` の `from = "src"` を削除するか、実際に `src/` に移す。今回は設定側を修正する方針。
- `poetry build` もしくは `poetry check` で設定が通ることを確認し、生成物に `app/` と `bot/` が含まれることを spot check。

### 3. リアクション同期ロジック
- `ChannelBridgeManager` にリアクションのペイロードを追跡する構造（例: `Dict[(message_id, emoji), Set[user_id]]`）を追加。
- `reaction_add` 時にセットへ追加し、空集合から初めて Bot リアクションを付与。
- `reaction_remove` 時にセットから削除し、最後のユーザーがいなくなったときのみ Bot リアクションを除去。
- Discord API の制限を考慮し、`PartialEmoji` もキーとして扱えるようハッシュ化戦略を決める。
- ユーザー操作が大量でもリークしないよう、元メッセージ削除時に追跡セットもクリア。

## 検証
1. `pyproject.toml` 修正後、`poetry run general-py-discord-bot` が `main.py` を起動することを確認（トークン未設定でも ModuleNotFoundError が出ない状態）。
2. `poetry build` で Wheel/Sdist を生成し、`tar tzf` / `zipinfo` で `app/` `bot/` が含まれることを確認。
3. ローカルでモックした `discord.Message` を使うユニットテスト、もしくは `pytest` でリアクション同期のユースケースを再現し、複数ユーザーのリアクションが正しく残ることを確認。

## リスクとフォローアップ
- リアクション状態を管理するためのメモリ使用量が増える。不要になったメッセージの情報を適切にクリーンアップする仕組みを実装すること。
- 実際の Discord API で `PartialEmoji`（カスタム絵文字）を扱う場合の挙動が要検証。単体テストでは `name` と `id` をキーにする前提で実装する。
