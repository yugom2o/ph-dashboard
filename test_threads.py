#!/usr/bin/env python3
"""
Threads API 疎通確認＆テスト投稿スクリプト
"""

import argparse
import io
import sys
from pathlib import Path

# Windows環境でのUTF-8出力対策
if sys.stdout is not None and sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.publishers import ThreadsPublisher


def main():
    parser = argparse.ArgumentParser(description="Threads API 疎通確認＆テスト投稿")
    parser.add_argument("--post", action="store_true", help="実際にテスト投稿を実行する")
    args = parser.parse_args()

    print("==================================================")
    print("🧵 Threads API 接続テスト")
    print("==================================================")

    publisher = ThreadsPublisher()

    if not publisher.is_configured:
        print("\n❌ エラー: .env に THREADS_ACCESS_TOKEN が設定されていません。")
        print("以下の行を .env に追加してください:")
        print("THREADS_ACCESS_TOKEN=あなたのアクセストークン")
        return

    print("\n[Step 1] アカウント情報とトークンの有効性を確認中...")
    profile = publisher.get_user_profile()

    if not profile:
        print("\n❌ トークンが無効か、接続に失敗しました。トークンを確認してください。")
        return

    user_id = profile.get("id")
    username = profile.get("username")
    name = profile.get("name")

    print("\n✅ 接続成功！ アカウント情報を取得しました:")
    print(f"  • ユーザー名: @{username}")
    print(f"  • アカウント名: {name}")
    print(f"  • Threads ユーザーID: {user_id}")

    if not args.post:
        print("\n💡 接続確認は完了です！")
        print("実際にテスト投稿を行うには、以下のコマンドを実行してください:")
        print("  python test_threads.py --post")
        print("==================================================")
        return

    print("\n[Step 2] テスト投稿を実行中...")
    test_text = (
        "Hello from Global Tech Radar! 🌐\n\n"
        "海外の最新AI・テックトレンドを配信するシステムとの自動連携テストです。\n\n"
        "#GlobalTech #AIツール"
    )

    post_id = publisher.publish_text(test_text)

    if post_id:
        print("\n🎉 テスト投稿が成功しました！")
        print(f"投稿ID: {post_id}")
        print(f"Threadsアプリまたはブラウザで @{username} のプロフィールを確認してください。")
    else:
        print("\n❌ 投稿に失敗しました。エラーログを確認してください。")

    print("==================================================")


if __name__ == "__main__":
    main()
