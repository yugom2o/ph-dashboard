import io
import json
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows 文字コード対策
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from config import DB_PATH, GITHUB_REPO, GITHUB_TOKEN
from src.collectors import ProductHuntRSSCollector
from src.enrichers import LPScraper
from src.evaluators import GeminiEvaluator
from src.reporters import HTMLReporter, MarkdownReporter
from src.reporters.github_uploader import GitHubUploader
from src.storage import Database


def main():
    print("==================================================")
    print("🚀 古いモックデータの全消去＆全プロダクト完全再分析開始")
    print("==================================================")

    db = Database()

    # 1. 古いモック・未完了評価の完全削除
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluations WHERE raw_json NOT LIKE '%original_summary_ja%'")
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"-> 古いモック評価データを削除しました: {deleted_count} 件")

    # 2. 最新RSSから10〜15件の最新プロダクトを確実に取得
    collector = ProductHuntRSSCollector()
    products = collector.fetch_daily_products(limit=15)
    print(f"-> 最新Product Huntプロダクト取得: {len(products)} 件")

    enricher = LPScraper()
    evaluator = GeminiEvaluator()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 3. 未分析または古いデータしかなかったプロダクトをすべて再分析
    for idx, p in enumerate(products, 1):
        print(f"\n[{idx}/{len(products)}] {p.name}")
        # すでに新しい形式で評価済みか確認
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT count(*) FROM evaluations e
                JOIN products pr ON e.product_id = pr.id
                WHERE (pr.ph_url = ? OR pr.id = ?) AND e.raw_json LIKE '%original_summary_ja%'
                """,
                (p.ph_url, p.id),
            )
            has_fresh = cursor.fetchone()[0] > 0

        if has_fresh:
            print("  -> 既に新方式で分析済み。スキップします。")
            continue

        print(f"  -> タグライン: {p.tagline}")
        lp_text = ""
        if p.official_url:
            print(f"  -> LP取得中: {p.official_url}")
            lp_text = enricher.fetch_lp_text(p.official_url) or ""

        print("  -> Gemini 3.5 Flash-Lite で詳細日本語解説＆具体ビジネス生成中...")
        res = evaluator.evaluate(p.name, p.tagline, p.description, lp_text)
        print(f"     判定: 【ランク {res.rank}】")
        print(f"     一言: {res.one_line_summary}")

        # DB保存
        p_dict = {
            "id": p.id,
            "name": p.name,
            "tagline": p.tagline,
            "description": p.description,
            "ph_url": p.ph_url,
            "official_url": p.official_url,
            "votes_count": p.votes_count,
            "category": p.category,
            "first_seen_date": today_str,
        }
        db.save_product(p_dict)
        db.save_evaluation(p.id, res.model_dump(), today_str)

    # 4. レポートおよびダッシュボードをクリーンなデータのみで再生成
    print("\n[レポート＆ダッシュボード再生成中...]")
    # 新方式で分析されたものだけを取得
    valid_items = []
    all_recent = db.get_all_recent_evaluations(limit=50)
    for it in all_recent:
        if it.get("original_summary_ja") or it.get("origNote") == "元プロダクトの機能概要 (日本語解説)":
            valid_items.append(it)

    print(f"-> 有効な高品質カード数: {len(valid_items)} 件")

    md_reporter = MarkdownReporter()
    html_reporter = HTMLReporter()

    md_file = md_reporter.generate_daily_report(valid_items, today_str)
    html_file = html_reporter.generate_dashboard(valid_items, today_str)
    print(f"-> 生成完了: {html_file.name}")

    # 5. GitHub リポジトリおよび GitHub Pages へのアップロード
    if GITHUB_TOKEN and GITHUB_REPO:
        print("\n[GitHub Pagesへ直接アップロード中...]")
        uploader = GitHubUploader()
        uploader.upload_file(html_file, target_path="index.html", commit_message="Update clean high-quality dashboard")
        uploader.upload_file(html_file, target_path="dashboard.html", commit_message="Update clean high-quality dashboard")
        uploader.upload_file(html_file, target_path="docs/index.html", commit_message="Update clean high-quality dashboard to docs")

    print("\n==================================================")
    print("🎉 全プロダクトの高品質再分析＆GitHub反映が完了しました！")
    print("==================================================")


if __name__ == "__main__":
    main()
