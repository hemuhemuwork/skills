# Skills

Claude Code用カスタムスキル集です。

## スキル一覧

### [chouseisan-poll](./chouseisan-poll/)

調整さん（https://chouseisan.com）でブラウザ操作により出欠調整イベントを自動作成するスキル。

- Playwrightによるヘッドレスブラウザ自動操作
- UIが変更されても毎回フォーム構造を確認して対応可能
- イベント名・候補日程・メモを指定して出欠表を作成し、共有URLを取得

**使用例:**
- 「日程調整したい」
- 「出欠表を作って」
- 「調整さんでイベント作って」

## インストール方法

プロジェクトの `.claude/skills/` ディレクトリにスキルフォルダをコピーしてください。

```bash
# 例: chouseisan-poll をプロジェクトに追加
cp -r chouseisan-poll /path/to/your-project/.claude/skills/
```

## 前提条件

- Python 3
- Playwright（`pip install playwright && playwright install chromium`）
