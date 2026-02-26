# Skills

Claude Code用カスタムスキル集です。

## スキル一覧

### [chouseisan-poll](./chouseisan-poll/)

調整さん（https://chouseisan.com）でブラウザ操作により出欠調整イベントを自動作成するスキル。

- Playwrightによるヘッドレスブラウザ自動操作
- UIが変更されても毎回フォーム構造を確認して対応可能
- イベント名・候補日程・メモを指定して出欠表を作成し、共有URLを取得

**使用例:** 「日程調整したい」「出欠表を作って」「調整さんでイベント作って」

---

### [x-scheduler](./x-scheduler/)

GitHub Actions + cron-job.org を使って X（旧Twitter）の予約投稿を管理するスキル。

- JSONファイルベースの予約管理（追加・一覧・キャンセル・履歴）
- GitHub Actions による自動投稿（最大10分の誤差）
- 返信・引用ツイートにも対応
- `setup` コマンドでワークフロー・スクリプトを自動生成

**使用例:** 「予約投稿したい」「明日の朝に投稿して」「投稿を予約して」

**必要なもの:**
- X Developer Account（API v2）
- GitHub リポジトリ（private推奨）
- cron-job.org アカウント（無料）

---

### [gcal-manager](./gcal-manager/)

Google Calendar API v3 を使用してカレンダーの予定管理を行うスキル。

- 指定期間の予定一覧取得
- busy/free（空き時間）判定
- 予定の新規作成
- OAuth 2.0 による安全な認証

**使用例:** 「今日の予定は？」「来週の空き時間を確認して」「カレンダーに予定を追加して」

**必要なもの:**
- Google Cloud Console プロジェクト（Calendar API 有効化済み）
- OAuth クライアントID（デスクトップアプリ）

## インストール方法

プロジェクトの `.claude/skills/` ディレクトリにスキルフォルダをコピーしてください。

```bash
# 例: x-scheduler をプロジェクトに追加
cp -r x-scheduler /path/to/your-project/.claude/skills/

# 例: gcal-manager をプロジェクトに追加
cp -r gcal-manager /path/to/your-project/.claude/skills/
```

各スキルの詳細なセットアップ手順は、スキルフォルダ内の `SKILL.md` を参照してください。

## 前提条件

- Python 3.10+
- 各スキルの個別の依存パッケージ（各 `SKILL.md` を参照）

## セキュリティ

- APIキー・認証トークンはコードに含めず、環境変数またはプロジェクト外のディレクトリで管理します
- 各スキルの `SKILL.md` に記載のセキュリティガイドラインに従ってください
