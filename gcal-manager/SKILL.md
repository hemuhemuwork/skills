---
name: gcal-manager
description: Googleカレンダーの予定管理スキル。「今日の予定は？」「来週の空き時間を確認して」「カレンダーに予定を追加して」といった要望に対応。予定の取得・空き時間確認・予定作成が可能。
---

# Google Calendar Manager

Google Calendar API v3を使用して、カレンダーの予定確認・空き時間判定・予定作成を行うClaude Codeスキルです。

## 初回セットアップ

### Step 1: Google Cloud Console でプロジェクトを作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（または既存のプロジェクトを選択）
3. **APIs & Services > Library** から **Google Calendar API** を検索して有効化

### Step 2: OAuth クライアントIDを作成

1. **APIs & Services > Credentials** に移動
2. **+ CREATE CREDENTIALS > OAuth client ID** をクリック
3. アプリケーションの種類で **Desktop app** を選択
4. 名前を入力して作成
5. **Download JSON** をクリックして `credentials.json` を保存

> **OAuth 同意画面の設定が必要な場合:** User Type を「外部」で作成し、テストユーザーに自分のGoogleアカウントを追加してください。

### Step 3: 認証ファイルを安全な場所に配置

```bash
# 認証ファイル用ディレクトリを作成
mkdir -p ~/.config/google-calendar

# credentials.json を配置
cp ~/Downloads/credentials.json ~/.config/google-calendar/

# パーミッションを制限（所有者のみ読み書き可能）
chmod 600 ~/.config/google-calendar/credentials.json
```

### Step 4: スキルをプロジェクトに配置

```bash
cp -r gcal-manager /path/to/your-project/.claude/skills/
```

### Step 5: 環境変数を設定

```bash
cd /path/to/your-project/.claude/skills/gcal-manager
cp .env.example .env
# 必要に応じて GOOGLE_CREDENTIALS_DIR のパスを変更
```

### Step 6: Python依存パッケージをインストール

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### Step 7: OAuth 認証を実行

```bash
python3 .claude/skills/gcal-manager/scripts/gcal.py auth
```

ブラウザが開き、Googleアカウントでの認証画面が表示されます。認証を完了すると `token.json` が生成されます。

## 使い方

### 予定一覧の取得

```bash
# 今日の予定
python3 .claude/skills/gcal-manager/scripts/gcal.py events --start today --end today

# 特定期間の予定
python3 .claude/skills/gcal-manager/scripts/gcal.py events --start 2026-03-01 --end 2026-03-07

# 特定カレンダーの予定
python3 .claude/skills/gcal-manager/scripts/gcal.py events --start today --end today --calendar-id someone@example.com
```

### 空き時間の確認（Busy/Free）

```bash
# 今週のbusy/freeサマリー
python3 .claude/skills/gcal-manager/scripts/gcal.py busy --start today --end +7d

# 特定期間
python3 .claude/skills/gcal-manager/scripts/gcal.py busy --start 2026-03-01 --end 2026-03-07
```

### 予定の作成

```bash
# 予定を追加
python3 .claude/skills/gcal-manager/scripts/gcal.py create \
  --summary "ミーティング" \
  --start "2026-03-01T10:00:00" \
  --end "2026-03-01T11:00:00" \
  --timezone "Asia/Tokyo"

# 場所と説明付き
python3 .claude/skills/gcal-manager/scripts/gcal.py create \
  --summary "クライアント打合せ" \
  --start "2026-03-01T14:00:00" \
  --end "2026-03-01T15:30:00" \
  --location "Zoom" \
  --description "Q1レビュー"
```

## コマンドリファレンス

| コマンド | 引数 | 説明 |
|---|---|---|
| `auth` | なし | OAuth初回認証を実行 |
| `events` | `--start`, `--end`, `--calendar-id`(任意) | 指定期間の予定一覧を取得 |
| `busy` | `--start`, `--end`, `--calendar-id`(任意) | busy/freeサマリーを取得 |
| `create` | `--summary`, `--start`, `--end`, `--timezone`(任意), `--description`(任意), `--location`(任意), `--calendar-id`(任意) | 予定を作成 |

### 日付指定フォーマット

| 形式 | 例 | 説明 |
|---|---|---|
| `today` | - | 今日 |
| `tomorrow` | - | 明日 |
| `YYYY-MM-DD` | `2026-03-01` | 特定日 |
| `+Nd` | `+7d` | 今日からN日後 |

## セキュリティに関する注意

### 認証ファイルの管理

- `credentials.json` と `token.json` は **プロジェクト外**（`~/.config/google-calendar/`）に保存されます
- これらのファイルは **絶対にGitリポジトリにコミットしないでください**
- ファイルのパーミッションは `600`（所有者のみ読み書き可能）に設定してください

### APIスコープ

このスキルは `https://www.googleapis.com/auth/calendar` スコープ（読み書き）を使用します。予定の閲覧だけでなく作成も行うためです。

読み取り専用で十分な場合は、`gcal.py` 内の `SCOPES` を以下に変更して `auth` を再実行してください：

```python
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
```

> **スコープを変更した場合:** 既存の `token.json` を削除してから `auth` コマンドを再実行する必要があります。

### LLMへの注意

- **Claude Codeに認証ファイル（credentials.json, token.json）の中身を読ませないでください。**
- `.env` ファイルもスキルローカルの設定ファイルであり、LLMに露出させる必要はありません。

## 前提条件

- Python 3.10+
- Google Cloud Console でプロジェクト作成済み & Calendar API 有効化済み
- 以下のPythonパッケージ：
  - `google-auth`
  - `google-auth-oauthlib`
  - `google-api-python-client`

## Resources

### scripts/
- `gcal.py` - Google Calendar API CLIスクリプト
