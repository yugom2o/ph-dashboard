import argparse
import base64
from datetime import datetime, timedelta, timezone
import io
import os
import sys
from pathlib import Path

# Windows環境・バックグラウンド実行(pythonw)での文字化けやNoneTypeエラー防止
LOG_FILE = Path(__file__).resolve().parent / "sync_reports.log"
if sys.stdout is not None:
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
else:
    # pythonw.exe などのヘッドレス環境ではログファイルへリダイレクト
    f_log = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    sys.stdout = f_log
    sys.stderr = f_log

import requests
from config import BASE_DIR, DATA_DIR, GITHUB_REPO, GITHUB_TOKEN, REPORTS_DIR

JST = timezone(timedelta(hours=9))


def get_headers():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[Error] .env に GITHUB_TOKEN または GITHUB_REPO が設定されていません。")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def pull_from_github(today_str: str) -> bool:
    """GitHubリポジトリから最新の reports/*.md, data/history.db, dashboard.html をローカルに同期
    本日分のレポートが取得できた場合は True を返す
    """
    headers = get_headers()
    print("==================================================")
    print(f"📥 GitHub ({GITHUB_REPO}) から最新データを取得中...")
    print(f"基準日付 (JST): {today_str}")
    print("==================================================")

    tree_url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/main?recursive=1"
    try:
        resp = requests.get(tree_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            print(f"[Warning] ツリー取得失敗: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"[Warning] GitHub接続エラー: {e}")
        return False

    tree = resp.json().get("tree", [])
    today_report_found = False
    synced_count = 0

    for item in tree:
        path_str = item["path"]
        is_target = (
            (path_str.startswith("reports/") and path_str.endswith(".md"))
            or path_str == "data/history.db"
            or path_str == "dashboard.html"
            or path_str == "docs/index.html"
        )
        if not is_target:
            continue

        if path_str == f"reports/{today_str}_ProductHunt日次分析レポート.md":
            today_report_found = True

        file_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path_str}"
        try:
            f_resp = requests.get(file_url, headers=headers, timeout=15)
            if f_resp.status_code == 200:
                content_b64 = f_resp.json().get("content", "")
                content_bytes = base64.b64decode(content_b64)
                local_file = BASE_DIR / path_str
                local_file.parent.mkdir(parents=True, exist_ok=True)

                if not local_file.exists() or local_file.read_bytes() != content_bytes:
                    local_file.write_bytes(content_bytes)
                    print(f"  [更新] {path_str}")
                    synced_count += 1
                else:
                    print(f"  [最新] {path_str}")
        except Exception as e:
            print(f"  [スキップ] {path_str}: {e}")

    print(f"\n🎉 同期完了！ (更新ファイル: {synced_count} 件)")
    return today_report_found


def main():
    parser = argparse.ArgumentParser(description="GitHubとローカルObsidianのインテリジェント同期ツール")
    parser.add_argument("--force-run", action="store_true", help="同期の成否にかかわらずローカル分析を強制実行")
    args = parser.parse_args()

    today_str = datetime.now(JST).strftime("%Y-%m-%d")

    # 1. まずGitHubから最新データを取得
    has_today = pull_from_github(today_str)

    # 2. 本日分のレポートがすでにGitHub上にある場合
    if has_today and not args.force_run:
        print(f"✅ 本日 ({today_str}) の分析レポートはすでにGitHub上で完了・同期済みです。")
        print("追加のAPI実行はスキップし、二重実行・重複を防止しました。")
        return

    # 3. 本日分がまだない場合（GitHub Actions未稼働または失敗時）はローカルで安全に実行
    print(f"\n[Info] 本日 ({today_str}) のレポートが未取得のため、ローカルでパイプラインを実行します...")
    from src.pipeline import DailyPipeline

    pipeline = DailyPipeline()
    pipeline.run(target_date=today_str)


if __name__ == "__main__":
    main()
