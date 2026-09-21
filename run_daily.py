import argparse
import io
import sys
from pathlib import Path

# Windows環境での文字化け・絵文字UnicodeEncodeError(cp932)防止
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# パスの追加
sys.path.insert(0, str(Path(__file__).resolve().parent))


from src.pipeline import DailyPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Product Hunt 日次収集＆日本市場ローカライズ事業判定システム"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="モックデータを使用してAPIキー消費なしでパイプラインをテスト実行",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="取得および分析するプロダクト数の上限 (デフォルト: config.py の DAILY_FETCH_LIMIT)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="過去に分析済みのプロダクトでもスキップせずに強制再分析を実行",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="分析対象日付 (YYYY-MM-DD形式。未指定時は本日)",
    )

    args = parser.parse_args()

    pipeline = DailyPipeline(is_mock=args.mock, force=args.force)
    pipeline.run(limit=args.limit, target_date=args.date)


if __name__ == "__main__":
    main()
