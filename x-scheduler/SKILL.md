---
name: x-scheduler
description: X（旧Twitter）の予約投稿をGitHub Actionsで管理するスキル。「予約投稿したい」「スケジュール投稿」「明日の朝に投稿して」「投稿を予約して」といった要望に対応。
---

# X-Scheduler

GitHub Actions を使って X（旧Twitter）の予約投稿を管理するClaude Codeスキルです。

## 仕組み

```
[Claude Code] → scheduler.py add → JSONファイル作成
    ↓
[git push] → GitHub リポジトリに反映
    ↓
[cron-job.org] → 10分ごとに repository_dispatch API を呼び出し
    ↓
[GitHub Actions] → post_due.py 実行 → 時刻チェック → X API で投稿
    ↓
[done/] に移動 → git commit & push
```

1. 予約投稿はプロジェクト内の `scheduled-posts/` ディレクトリにJSONファイルとして保存
2. cron-job.org が10分ごとに GitHub API（`repository_dispatch`）を叩いてワークフローを起動
3. ワークフローが投稿時刻を過ぎたものを自動投稿
4. 投稿完了後、JSONファイルは `scheduled-posts/done/` に移動される

> **Note:** GitHub Actions の cron（schedule トリガー）は遅延・スキップが頻発するため、cron-job.org による外部トリガーを推奨しています。

## 初回セットアップ

### Step 1: スキルをプロジェクトに配置

```bash
cp -r x-scheduler /path/to/your-project/.claude/skills/
```

### Step 2: プロジェクトのセットアップ

```bash
python3 .claude/skills/x-scheduler/scripts/scheduler.py setup
```

これにより以下が自動生成されます：
- `scheduled-posts/` ディレクトリ
- `scheduled-posts/post_due.py`（GitHub Actionsから実行されるスクリプト）
- `.github/workflows/x-scheduled-post.yml`

### Step 3: X API キーの取得

1. [X Developer Portal](https://developer.x.com/) でアプリを作成
2. **OAuth 1.0a** の User Authentication を有効化（Read and Write）
3. 以下の4つのキーを取得：
   - API Key
   - API Key Secret
   - Access Token
   - Access Token Secret

### Step 4: GitHub Secrets の設定

リポジトリの **Settings > Secrets and variables > Actions** に以下を登録：

| Secret名 | 値 |
|---|---|
| `X_API_KEY` | API Key |
| `X_API_KEY_SECRET` | API Key Secret |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_TOKEN_SECRET` | Access Token Secret |

### Step 5: cron-job.org の設定

[cron-job.org](https://cron-job.org/) で無料アカウントを作成し、以下のジョブを作成：

| 項目 | 設定値 |
|---|---|
| URL | `https://api.github.com/repos/{owner}/{repo}/dispatches` |
| Method | POST |
| Schedule | 10分ごと（`*/10 * * * *`） |

**Headers:**
```
Authorization: Bearer {GitHubのPersonal Access Token}
Accept: application/vnd.github+v3+json
Content-Type: application/json
```

**Body:**
```json
{"event_type":"schedule-check"}
```

> **GitHub PAT の権限:** `repo` スコープが必要です（privateリポジトリの場合）。publicリポジトリなら `public_repo` で十分です。

### Step 6: commit & push

```bash
git add scheduled-posts/ .github/
git commit -m "feat: add X scheduled posting via GitHub Actions"
git push
```

## 使い方

### 予約投稿を追加

```bash
python3 .claude/skills/x-scheduler/scripts/scheduler.py add \
  --text "投稿内容" \
  --datetime "2026-02-25 09:00" \
  --timezone "Asia/Tokyo"
```

追加後は必ず commit & push：

```bash
git add scheduled-posts/ && git commit -m "schedule: 投稿予約" && git push
```

**オプション:**
- `--reply-to <id>`: 返信先ツイートID
- `--quote <id>`: 引用元ツイートID
- `--label <ラベル>`: 管理用ラベル（任意）
- `--timezone`: タイムゾーン（デフォルト: `Asia/Tokyo`）

### 予約一覧を確認

```bash
python3 .claude/skills/x-scheduler/scripts/scheduler.py list
```

### 予約をキャンセル

```bash
python3 .claude/skills/x-scheduler/scripts/scheduler.py cancel <post_id>
```

キャンセル後も commit & push が必要。

### 投稿履歴を確認

```bash
python3 .claude/skills/x-scheduler/scripts/scheduler.py history
```

## 予約投稿JSONの形式

```json
{
  "id": "20260225_090000_a1b2c3",
  "text": "投稿内容",
  "scheduled_at": "2026-02-25T09:00:00+09:00",
  "created_at": "2026-02-24T20:00:00+09:00",
  "status": "pending",
  "label": "朝の投稿",
  "reply_to": null,
  "quote_tweet_id": null
}
```

## セキュリティに関する注意

- **APIキーは絶対にコードやJSONファイルに含めないでください。** GitHub Secrets のみに保存してください。
- 予約投稿の内容は Git の commit 履歴に残ります。**リポジトリは private にすることを強く推奨**します。
- cron-job.org に登録する GitHub PAT は最小限の権限に絞ってください。
- GitHub PAT はcron-job.orgの設定画面のみに保存され、コードには含まれません。

## 前提条件

- Python 3.10+
- [tweepy](https://pypi.org/project/tweepy/) (`pip install tweepy`)
- GitHub リポジトリ
- X Developer Account（API v2 アクセス）

## 注意事項

- 投稿タイミングは最大10分の誤差があります（cron-job.org の実行間隔による）
- 予約追加後は必ず commit & push してください（pushしないとGitHub Actionsに認識されません）
