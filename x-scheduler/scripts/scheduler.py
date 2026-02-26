#!/usr/bin/env python3
"""
X-Scheduler: X予約投稿の管理スクリプト
- add: 予約投稿を追加
- list: 予約一覧を表示
- cancel: 予約をキャンセル
- history: 投稿済み履歴を表示
- post-due: 投稿時刻を過ぎたものを投稿（GitHub Actionsから呼ばれる）
- setup: 初回セットアップ（ディレクトリ・ワークフロー生成）
"""

import os
import sys
import json
import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


def get_project_root() -> Path:
    """プロジェクトルートを取得（カレントディレクトリから.git探索）"""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / '.git').exists():
            return parent
    return cwd


def get_scheduled_dir(project_root: Path) -> Path:
    return project_root / 'scheduled-posts'


def get_done_dir(project_root: Path) -> Path:
    return project_root / 'scheduled-posts' / 'done'


def glob_json(directory: Path) -> list[Path]:
    """*.json をglobし、macOSの ._ メタデータファイルを除外"""
    return sorted(f for f in directory.glob('*.json') if not f.name.startswith('._'))


def generate_post_id(scheduled_at: datetime) -> str:
    """投稿IDを生成"""
    ts = scheduled_at.strftime('%Y%m%d_%H%M%S')
    hash_part = hashlib.md5(f"{ts}{datetime.now().isoformat()}".encode()).hexdigest()[:6]
    return f"{ts}_{hash_part}"


# ============================================================
# add
# ============================================================
def cmd_add(args, project_root: Path):
    """予約投稿を追加"""
    scheduled_dir = get_scheduled_dir(project_root)
    scheduled_dir.mkdir(parents=True, exist_ok=True)

    tz = ZoneInfo(args.timezone)
    # パース: "2026-02-25 09:00" or "2026-02-25T09:00"
    dt_str = args.datetime.replace('T', ' ')
    try:
        naive = datetime.strptime(dt_str, '%Y-%m-%d %H:%M')
    except ValueError:
        try:
            naive = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"エラー: 日時の形式が不正です: {args.datetime}", file=sys.stderr)
            print("形式: YYYY-MM-DD HH:MM", file=sys.stderr)
            sys.exit(1)

    scheduled_at = naive.replace(tzinfo=tz)
    now = datetime.now(tz)

    if scheduled_at <= now:
        print(f"警告: 指定日時 ({scheduled_at.isoformat()}) は過去です。", file=sys.stderr)
        print("予約はされますが、次のcron実行時に即座に投稿されます。", file=sys.stderr)

    post_id = generate_post_id(scheduled_at)

    post_data = {
        "id": post_id,
        "text": args.text,
        "scheduled_at": scheduled_at.isoformat(),
        "created_at": now.isoformat(),
        "status": "pending",
        "label": args.label or "",
        "reply_to": args.reply_to,
        "quote_tweet_id": args.quote,
    }

    filepath = scheduled_dir / f"{post_id}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)

    print(f"予約投稿を追加しました")
    print(f"  ID: {post_id}")
    print(f"  投稿予定: {scheduled_at.strftime('%Y-%m-%d %H:%M')} ({args.timezone})")
    print(f"  内容: {args.text[:50]}{'...' if len(args.text) > 50 else ''}")
    print(f"  ファイル: {filepath.relative_to(project_root)}")

    return post_data


# ============================================================
# list
# ============================================================
def cmd_list(args, project_root: Path):
    """予約一覧を表示"""
    scheduled_dir = get_scheduled_dir(project_root)
    if not scheduled_dir.exists():
        print("予約投稿はありません。")
        return

    posts = []
    for f in glob_json(scheduled_dir):
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if data.get('status') == 'pending':
                posts.append(data)

    if not posts:
        print("予約投稿はありません。")
        return

    posts.sort(key=lambda x: x['scheduled_at'])
    print(f"予約投稿一覧 ({len(posts)}件):")
    print("-" * 60)
    for p in posts:
        label = f" [{p['label']}]" if p.get('label') else ""
        dt = datetime.fromisoformat(p['scheduled_at'])
        print(f"  {p['id']}{label}")
        print(f"    予定: {dt.strftime('%Y-%m-%d %H:%M %Z')}")
        text_preview = p['text'][:60].replace('\n', ' ')
        print(f"    内容: {text_preview}{'...' if len(p['text']) > 60 else ''}")
        print()


# ============================================================
# cancel
# ============================================================
def cmd_cancel(args, project_root: Path):
    """予約をキャンセル"""
    scheduled_dir = get_scheduled_dir(project_root)
    filepath = scheduled_dir / f"{args.post_id}.json"

    if not filepath.exists():
        print(f"エラー: 予約投稿が見つかりません: {args.post_id}", file=sys.stderr)
        sys.exit(1)

    filepath.unlink()
    print(f"予約投稿をキャンセルしました: {args.post_id}")


# ============================================================
# history
# ============================================================
def cmd_history(args, project_root: Path):
    """投稿済み履歴を表示"""
    done_dir = get_done_dir(project_root)
    if not done_dir.exists():
        print("投稿履歴はありません。")
        return

    posts = []
    for f in glob_json(done_dir):
        with open(f, 'r', encoding='utf-8') as fh:
            posts.append(json.load(fh))

    if not posts:
        print("投稿履歴はありません。")
        return

    posts.sort(key=lambda x: x.get('posted_at', x['scheduled_at']), reverse=True)
    print(f"投稿履歴 ({len(posts)}件):")
    print("-" * 60)
    for p in posts:
        posted = p.get('posted_at', '不明')
        tweet_url = p.get('tweet_url', '')
        print(f"  {p['id']}")
        print(f"    投稿日時: {posted}")
        if tweet_url:
            print(f"    URL: {tweet_url}")
        text_preview = p['text'][:60].replace('\n', ' ')
        print(f"    内容: {text_preview}{'...' if len(p['text']) > 60 else ''}")
        print()


# ============================================================
# post-due: GitHub Actions から呼ばれる
# ============================================================
def cmd_post_due(args, project_root: Path):
    """投稿時刻を過ぎた予約を投稿"""
    scheduled_dir = get_scheduled_dir(project_root)
    done_dir = get_done_dir(project_root)

    if not scheduled_dir.exists():
        print("scheduled-posts/ ディレクトリがありません。")
        return

    done_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    posted_count = 0

    for f in glob_json(scheduled_dir):
        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        if data.get('status') != 'pending':
            continue

        scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        if scheduled_at > now:
            continue

        # 投稿実行
        print(f"投稿中: {data['id']} ...")
        try:
            result = post_to_x(data)
            data['status'] = 'posted'
            data['posted_at'] = datetime.now(timezone.utc).isoformat()
            data['tweet_id'] = result.get('tweet_id')
            data['tweet_url'] = result.get('url', '')
            print(f"  成功: {result.get('url', '')}")
        except Exception as e:
            data['status'] = 'failed'
            data['error'] = str(e)
            data['posted_at'] = datetime.now(timezone.utc).isoformat()
            print(f"  失敗: {e}", file=sys.stderr)

        # done/ に移動
        done_path = done_dir / f.name
        with open(done_path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        f.unlink()
        posted_count += 1

    print(f"\n処理完了: {posted_count}件投稿しました。")


def post_to_x(data: dict) -> dict:
    """X APIで投稿する（tweepyを使用）"""
    try:
        import tweepy
    except ImportError:
        raise RuntimeError("tweepy がインストールされていません: pip install tweepy")

    api_key = os.getenv('X_API_KEY')
    api_key_secret = os.getenv('X_API_KEY_SECRET')
    access_token = os.getenv('X_ACCESS_TOKEN')
    access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        raise ValueError(
            "X API認証情報が設定されていません。"
            "GitHub Secrets に X_API_KEY, X_API_KEY_SECRET, "
            "X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET を設定してください。"
        )

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    kwargs = {"text": data['text']}
    if data.get('reply_to'):
        kwargs["in_reply_to_tweet_id"] = data['reply_to']
    if data.get('quote_tweet_id'):
        kwargs["quote_tweet_id"] = data['quote_tweet_id']

    response = client.create_tweet(**kwargs)

    return {
        "success": True,
        "tweet_id": response.data['id'],
        "text": response.data['text'],
        "url": f"https://x.com/i/status/{response.data['id']}",
    }


# ============================================================
# setup: 初回セットアップ
# ============================================================
WORKFLOW_YAML = """\
name: X Scheduled Post

on:
  repository_dispatch:
    types: [schedule-check]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  post-scheduled:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Check for pending posts
        id: check
        run: |
          if ls scheduled-posts/*.json 1>/dev/null 2>&1; then
            echo "has_posts=true" >> $GITHUB_OUTPUT
          else
            echo "has_posts=false" >> $GITHUB_OUTPUT
            echo "No pending posts found. Skipping."
          fi

      - name: Set up Python
        if: steps.check.outputs.has_posts == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        if: steps.check.outputs.has_posts == 'true'
        run: pip install tweepy

      - name: Post due tweets
        if: steps.check.outputs.has_posts == 'true'
        env:
          X_API_KEY: ${{ secrets.X_API_KEY }}
          X_API_KEY_SECRET: ${{ secrets.X_API_KEY_SECRET }}
          X_ACCESS_TOKEN: ${{ secrets.X_ACCESS_TOKEN }}
          X_ACCESS_TOKEN_SECRET: ${{ secrets.X_ACCESS_TOKEN_SECRET }}
        run: python3 scheduled-posts/post_due.py

      - name: Commit changes
        if: steps.check.outputs.has_posts == 'true'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add scheduled-posts/
          if git diff --cached --quiet; then
            echo "No changes to commit"
          else
            git commit -m "chore: update scheduled posts status"
            git push
          fi

      - name: Keepalive
        run: echo "Workflow alive at $(date -u)"
"""

POST_DUE_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"
GitHub Actions から呼ばれる予約投稿実行スクリプト。
scheduled-posts/ 内の pending な投稿を時刻チェックして投稿する。
\"\"\"

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    import tweepy
except ImportError:
    print("tweepy is required: pip install tweepy")
    sys.exit(1)


def post_to_x(data: dict) -> dict:
    api_key = os.getenv('X_API_KEY')
    api_key_secret = os.getenv('X_API_KEY_SECRET')
    access_token = os.getenv('X_ACCESS_TOKEN')
    access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')

    if not all([api_key, api_key_secret, access_token, access_token_secret]):
        raise ValueError("X API credentials not set in environment/secrets.")

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_key_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    kwargs = {"text": data['text']}
    if data.get('reply_to'):
        kwargs["in_reply_to_tweet_id"] = data['reply_to']
    if data.get('quote_tweet_id'):
        kwargs["quote_tweet_id"] = data['quote_tweet_id']

    response = client.create_tweet(**kwargs)
    return {
        "tweet_id": response.data['id'],
        "url": f"https://x.com/i/status/{response.data['id']}",
    }


def main():
    base_dir = Path(__file__).parent
    done_dir = base_dir / 'done'
    done_dir.mkdir(exist_ok=True)

    now = datetime.now(timezone.utc)
    posted = 0

    for f in sorted(base_dir.glob('*.json')):
        if f.name.startswith('._'):
            continue

        with open(f, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        if data.get('status') != 'pending':
            continue

        scheduled_at = datetime.fromisoformat(data['scheduled_at'])
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        # UTC に変換して比較
        scheduled_utc = scheduled_at.astimezone(timezone.utc)
        if scheduled_utc > now:
            print(f"Skip (not yet): {data['id']} scheduled at {scheduled_at.isoformat()}")
            continue

        print(f"Posting: {data['id']} ...")
        try:
            result = post_to_x(data)
            data['status'] = 'posted'
            data['posted_at'] = now.isoformat()
            data['tweet_id'] = result['tweet_id']
            data['tweet_url'] = result['url']
            print(f"  OK: {result['url']}")
        except Exception as e:
            data['status'] = 'failed'
            data['error'] = str(e)
            data['posted_at'] = now.isoformat()
            print(f"  FAILED: {e}", file=sys.stderr)

        # done/ に移動
        done_path = done_dir / f.name
        with open(done_path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        f.unlink()
        posted += 1

    print(f"\\nDone: {posted} post(s) processed.")


if __name__ == '__main__':
    main()
"""


def cmd_setup(args, project_root: Path):
    """初回セットアップ"""
    # scheduled-posts/ ディレクトリ
    scheduled_dir = get_scheduled_dir(project_root)
    done_dir = get_done_dir(project_root)
    scheduled_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)

    # .gitkeep
    gitkeep = done_dir / '.gitkeep'
    if not gitkeep.exists():
        gitkeep.touch()

    # post_due.py（GitHub Actions から実行されるスクリプト）
    post_due_path = scheduled_dir / 'post_due.py'
    with open(post_due_path, 'w', encoding='utf-8') as f:
        f.write(POST_DUE_SCRIPT)
    os.chmod(post_due_path, 0o755)

    # .github/workflows/
    workflows_dir = project_root / '.github' / 'workflows'
    workflows_dir.mkdir(parents=True, exist_ok=True)

    workflow_path = workflows_dir / 'x-scheduled-post.yml'
    with open(workflow_path, 'w', encoding='utf-8') as f:
        f.write(WORKFLOW_YAML)

    print("セットアップ完了!")
    print()
    print("作成されたファイル:")
    print(f"  {scheduled_dir.relative_to(project_root)}/")
    print(f"  {scheduled_dir.relative_to(project_root)}/post_due.py")
    print(f"  {done_dir.relative_to(project_root)}/")
    print(f"  {workflow_path.relative_to(project_root)}")
    print()
    print("次のステップ:")
    print("  1. GitHubリポジトリの Settings > Secrets and variables > Actions に以下を設定:")
    print("     - X_API_KEY")
    print("     - X_API_KEY_SECRET")
    print("     - X_ACCESS_TOKEN")
    print("     - X_ACCESS_TOKEN_SECRET")
    print("  2. cron-job.org でジョブを作成（詳細は SKILL.md を参照）")
    print("  3. 変更を commit & push:")
    print("     git add scheduled-posts/ .github/")
    print("     git commit -m 'feat: add X scheduled posting via GitHub Actions'")
    print("     git push")


# ============================================================
# main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='X予約投稿マネージャー')
    subparsers = parser.add_subparsers(dest='command', help='コマンド')

    # add
    add_parser = subparsers.add_parser('add', help='予約投稿を追加')
    add_parser.add_argument('--text', '-t', required=True, help='投稿内容')
    add_parser.add_argument('--datetime', '-d', required=True, help='投稿日時 (YYYY-MM-DD HH:MM)')
    add_parser.add_argument('--timezone', '-tz', default='Asia/Tokyo', help='タイムゾーン (デフォルト: Asia/Tokyo)')
    add_parser.add_argument('--reply-to', help='返信先ツイートID')
    add_parser.add_argument('--quote', help='引用元ツイートID')
    add_parser.add_argument('--label', '-l', help='管理用ラベル')

    # list
    subparsers.add_parser('list', help='予約一覧を表示')

    # cancel
    cancel_parser = subparsers.add_parser('cancel', help='予約をキャンセル')
    cancel_parser.add_argument('post_id', help='キャンセルする投稿ID')

    # history
    subparsers.add_parser('history', help='投稿済み履歴を表示')

    # post-due (GitHub Actions用)
    subparsers.add_parser('post-due', help='投稿時刻を過ぎたものを投稿')

    # setup
    subparsers.add_parser('setup', help='初回セットアップ')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    project_root = get_project_root()

    if args.command == 'add':
        cmd_add(args, project_root)
    elif args.command == 'list':
        cmd_list(args, project_root)
    elif args.command == 'cancel':
        cmd_cancel(args, project_root)
    elif args.command == 'history':
        cmd_history(args, project_root)
    elif args.command == 'post-due':
        cmd_post_due(args, project_root)
    elif args.command == 'setup':
        cmd_setup(args, project_root)


if __name__ == '__main__':
    main()
