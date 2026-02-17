#!/usr/bin/env python3
"""
調整さん (chouseisan.com) ブラウザ自動操作CLI

Usage:
    chouseisan.py recon                          # トップページのフォーム構造を取得
    chouseisan.py create --name NAME --dates DATES [--memo MEMO]  # イベント作成

フォーム構造はreconで毎回確認し、UIの変更に対応する。
"""

import argparse
import json
import sys
from playwright.sync_api import sync_playwright


CHOUSEISAN_URL = "https://chouseisan.com/"


def cmd_recon(_args):
    """トップページのフォーム構造（id/name属性、placeholder、ボタン）を取得して出力。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CHOUSEISAN_URL, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # フォーム要素を収集
        form_info = page.evaluate("""() => {
            const results = { inputs: [], textareas: [], buttons: [], checkboxes: [], selects: [] };

            document.querySelectorAll('input:not([type=hidden])').forEach(el => {
                results.inputs.push({
                    id: el.id, name: el.name, type: el.type,
                    placeholder: el.placeholder, value: el.value,
                    label: el.labels?.[0]?.textContent?.trim() || ''
                });
            });

            document.querySelectorAll('textarea').forEach(el => {
                results.textareas.push({
                    id: el.id, name: el.name,
                    placeholder: el.placeholder,
                    label: el.labels?.[0]?.textContent?.trim() || ''
                });
            });

            document.querySelectorAll('button, input[type=submit], a.btn, .btn').forEach(el => {
                results.buttons.push({
                    id: el.id, text: el.textContent?.trim(),
                    type: el.type || el.tagName, classes: el.className
                });
            });

            document.querySelectorAll('input[type=checkbox]').forEach(el => {
                results.checkboxes.push({
                    id: el.id, name: el.name, checked: el.checked,
                    label: el.labels?.[0]?.textContent?.trim() || ''
                });
            });

            document.querySelectorAll('select').forEach(el => {
                const options = [...el.options].map(o => ({ value: o.value, text: o.text }));
                results.selects.push({ id: el.id, name: el.name, options: options });
            });

            return results;
        }""")

        page.screenshot(path="/tmp/chouseisan_recon.png", full_page=True)
        browser.close()

    print(json.dumps(form_info, ensure_ascii=False, indent=2))
    print(f"\nScreenshot: /tmp/chouseisan_recon.png", file=sys.stderr)


def cmd_create(args):
    """イベントを作成して共有URLを返す。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(CHOUSEISAN_URL, timeout=30000)
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # イベント名
        page.fill("#name", args.name)

        # 日程候補
        page.fill("#kouho", args.dates)

        # メモ（任意）
        if args.memo:
            page.fill("#comment", args.memo)

        page.wait_for_timeout(500)
        page.screenshot(path="/tmp/chouseisan_before_submit.png", full_page=True)

        # 送信
        page.click("#createBtn")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(5000)

        page.screenshot(path="/tmp/chouseisan_result.png", full_page=True)
        url = page.url

        # 結果ページから共有URLを抽出
        share_url = page.evaluate("""() => {
            const input = document.querySelector('input[type=text][readonly], input[value*="chouseisan.com/s"]');
            if (input) return input.value;
            const el = document.querySelector('.text-url, #shareUrl, [class*=url]');
            if (el) return el.textContent?.trim();
            // テキスト内からURL抽出
            const body = document.body.innerText;
            const m = body.match(/https:\\/\\/chouseisan\\.com\\/s\\?h=[a-f0-9]+/);
            return m ? m[0] : null;
        }""")

        browser.close()

    result = {
        "page_url": url,
        "share_url": share_url,
        "event_name": args.name,
        "dates": args.dates,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="調整さん CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # recon
    subparsers.add_parser("recon", help="フォーム構造を取得")

    # create
    create_parser = subparsers.add_parser("create", help="イベント作成")
    create_parser.add_argument("--name", required=True, help="イベント名")
    create_parser.add_argument("--dates", required=True, help="日程候補（改行区切り）")
    create_parser.add_argument("--memo", default="", help="メモ（任意）")

    args = parser.parse_args()
    commands = {
        "recon": cmd_recon,
        "create": cmd_create,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
