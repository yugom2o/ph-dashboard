#!/usr/bin/env python3
"""
Global Tech Radar 週次トレンド分析 & note/ニュースレター原稿生成スクリプト

過去1週間に蓄積された海外最新プロダクトデータを集計し、
Geminiでマクロトレンド総括、注目カテゴリ、厳選ピックアップ、
note/ニュースレター向け完成原稿、X発信ツリー案を自動生成します。
"""

import argparse
import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windows環境でのUTF-8出力対策
if sys.stdout is not None and sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# パスの追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.notifiers import WebhookNotifier
from src.reporters import WeeklyReporter
from src.storage import Database

JST = timezone(timedelta(hours=9))


def main():
    parser = argparse.ArgumentParser(description="Global Tech Radar 週次トレンド生成")
    parser.add_argument("--days", type=int, default=7, help="集計対象の日数 (デフォルト: 7)")
    parser.add_argument("--end-date", type=str, default=None, help="集計終了日 (YYYY-MM-DD, デフォルト: 今日)")
    parser.add_argument("--mock", action="store_true", help="モックモードで実行 (Gemini API消費なし)")
    args = parser.parse_args()

    today = datetime.now(JST)
    if args.end_date:
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=JST)
    else:
        end_dt = today

    start_dt = end_dt - timedelta(days=args.days - 1)
    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")

    print("==================================================")
    print(f"📊 Global Tech Radar 週次トレンド分析開始")
    print(f"集計期間: {start_str} 〜 {end_str} ({args.days}日間)")
    print(f"モード: {'モック (テスト)' if args.mock else '実動 (Gemini分析)'}")
    print("==================================================")

    db = Database()
    items = db.get_evaluations_by_date_range(start_str, end_str)

    if not items:
        print(f"[Info] 該当期間 ({start_str}〜{end_str}) のデータが0件のため、直近の評価データを取得します...")
        items = db.get_all_recent_evaluations(limit=30)

    print(f"-> 分析対象プロダクト: {len(items)} 件")
    s_count = sum(1 for it in items if it.get("rank") == "S")
    a_count = sum(1 for it in items if it.get("rank") == "A")
    print(f"-> 内訳: Sランク {s_count}件 / Aランク {a_count}件")

    reporter = WeeklyReporter()
    out_file = reporter.generate_weekly_report(
        items=items,
        start_date=start_str,
        end_date=end_str,
        is_mock=args.mock,
    )

    print(f"\n🎉 週報生成が完了しました！")
    print(f"保存先: {out_file}")

    # Webhook通知
    notifier = WebhookNotifier()
    if notifier.is_configured:
        print("\nWebhookへ週報完成通知を送信中...")
        msg = (
            f"📰 **【Global Tech Radar】週刊トレンドレポート発行！**\n"
            f"期間: {start_str} 〜 {end_str} (計{len(items)}件)\n"
            f"Sランク: {s_count}件 | Aランク: {a_count}件\n"
            f"Obsidianノート: `{out_file.name}` にnote/ニュースレター用の完成原稿を出力しました。"
        )
        notifier._post_payload(msg)

    print("==================================================")


if __name__ == "__main__":
    main()
