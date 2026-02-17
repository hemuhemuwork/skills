---
name: chouseisan-poll
description: 調整さん(chouseisan.com)でブラウザ操作により出欠調整イベントを作成するスキル。「日程調整したい」「出欠表を作って」「調整さんでイベント作って」「候補日で投票ページ作って」といった要望に対応。Playwrightでブラウザを自動操作し、UIが変わっても都度フォーム構造を確認して対応する。
---

# 調整さん (chouseisan.com) イベント作成

## 前提条件

- Python 3 + Playwright がインストール済み（`pip install playwright && playwright install chromium`）

## ワークフロー

### Step 1: フォーム構造の確認（毎回実行）

UIの変更に対応するため、イベント作成前に必ずreconを実行してフォーム構造を確認する。

```bash
python3 .claude/skills/chouseisan-poll/scripts/chouseisan.py recon
```

出力: フォーム要素のid/name/placeholder/ボタン一覧（JSON）+ スクリーンショット `/tmp/chouseisan_recon.png`

reconの結果、フォーム構造が `scripts/chouseisan.py` のセレクタ（`#name`, `#kouho`, `#comment`, `#createBtn`）と異なる場合は、スクリプトのセレクタを修正してから実行する。

### Step 2: イベント作成

```bash
python3 .claude/skills/chouseisan-poll/scripts/chouseisan.py create \
  --name "イベント名" \
  --dates "3/21(土)
3/27(金)
3/28(土)" \
  --memo "メモ（任意）"
```

出力: 作成されたイベントの共有URL（JSON）+ スクリーンショット `/tmp/chouseisan_result.png`

### 日程候補の書式

- 改行区切りで1行1候補
- 例: `3/21(土) 11:00〜`, `3/27(金)`, `2026-03-28`
- 時刻を含める場合はイベント名か各行に記載

## セレクタのフォールバック

reconで取得したフォーム構造から、以下のデフォルトセレクタが変わっていないか確認する:

| 要素 | デフォルトセレクタ |
|---|---|
| イベント名 | `#name` |
| 日程候補 | `#kouho` |
| メモ | `#comment` |
| 送信ボタン | `#createBtn` |

セレクタが変わっている場合は `scripts/chouseisan.py` の `cmd_create` 関数内のセレクタを更新する。

## Resources

### scripts/
- `chouseisan.py` - 調整さんブラウザ自動操作CLI（recon / create）
