from datetime import datetime
from typing import Optional
from config import DAILY_FETCH_LIMIT, PRODUCTHUNT_TOKEN
from src.collectors import ProductHuntAPICollector, ProductHuntRSSCollector
from src.enrichers import LPScraper
from src.evaluators import GeminiEvaluator
from src.reporters import HTMLReporter, MarkdownReporter
from src.reporters.github_uploader import GitHubUploader
from src.storage import Database


class DailyPipeline:
    def __init__(self, is_mock: bool = False, force: bool = False):
        self.is_mock = is_mock
        self.force = force
        self.db = Database()
        self.enricher = LPScraper()
        self.evaluator = GeminiEvaluator()
        self.md_reporter = MarkdownReporter()
        self.html_reporter = HTMLReporter()
        self.github_uploader = GitHubUploader()


        # コレクター選定
        if PRODUCTHUNT_TOKEN and not is_mock:
            self.collector = ProductHuntAPICollector(PRODUCTHUNT_TOKEN)
        else:
            self.collector = ProductHuntRSSCollector()

    def run(self, limit: Optional[int] = None, target_date: Optional[str] = None):
        fetch_limit = limit or DAILY_FETCH_LIMIT
        today_str = target_date or datetime.now().strftime("%Y-%m-%d")

        print(f"==================================================")
        print(f"🚀 Product Hunt 日次分析パイプライン開始: {today_str}")
        print(f"モード: {'モック (テスト)' if self.is_mock else '実動 (Gemini + Grounding)'} / 上限: {fetch_limit}件")
        print(f"==================================================")

        # 1. プロダクト収集
        print("\n[Step 1/5] Product Huntから最新プロダクトを取得中...")
        if self.is_mock:
            from src.collectors.base import ProductItem
            products = [
                ProductItem(
                    id="lead-sparker",
                    name="Lead Sparker",
                    tagline="Turn any brand URL into a ready-to-send insight deck",
                    description="Enter a company website URL to generate personalized pitch decks and pain point analysis in minutes.",
                    ph_url="https://www.producthunt.com/products/lead-sparker",
                    official_url="https://leadsparker.com",
                    votes_count=482,
                    category="B2B Sales / AI Pitch",
                ),
                ProductItem(
                    id="jevtown",
                    name="Jevtown",
                    tagline="10,000 AI readers react to your post before you publish it",
                    description="Simulate reader reactions across diverse demographic personas before going live on social media.",
                    ph_url="https://www.producthunt.com/products/jevtown",
                    official_url="https://jevtown.ai",
                    votes_count=350,
                    category="Social / PR / Marketing",
                ),
                ProductItem(
                    id="supacut",
                    name="Supacut",
                    tagline="Quickly turn interview footage into a rough cut",
                    description="Upload raw interview clips to automatically extract key moments, remove filler words, and export timeline.",
                    ph_url="https://www.producthunt.com/products/supacut",
                    official_url="https://supacut.video",
                    votes_count=295,
                    category="Video Editing / Creator",
                ),
            ][:fetch_limit]
        else:
            products = self.collector.fetch_daily_products(limit=fetch_limit)

        print(f"-> 取得完了: {len(products)} 件")

        # 2. 履歴照合と重複除外
        print("\n[Step 2/5] 履歴DBとの照合・重複チェック...")
        target_products = []
        for p in products:
            if not self.force and self.db.is_already_analyzed(p.ph_url):
                print(f"  [スキップ済] {p.name} (既に評価済み)")
            else:
                target_products.append(p)

        print(f"-> 新規分析対象: {len(target_products)} 件")

        # 3. LPテキスト取得 & 4. 日本市場評価
        print("\n[Step 3-4/5] LP情報補完 & Geminiによる日本市場ローカライズ分析...")
        for idx, p in enumerate(target_products, start=1):
            print(f"\n--- [{idx}/{len(target_products)}] {p.name} ---")
            print(f"  タグライン: {p.tagline}")

            lp_text = ""
            if p.official_url and not self.is_mock:
                print(f"  公式サイトをクロール中: {p.official_url}")
                lp_text = self.enricher.fetch_lp_text(p.official_url) or ""
                if lp_text:
                    print(f"  -> LPテキスト抽出成功: {len(lp_text)}文字")

            print("  AI評価中 (競合Web検索 + タイムマシン事業判定)...")
            eval_result = self.evaluator.evaluate(
                product_name=p.name,
                tagline=p.tagline,
                description=p.description,
                lp_text=lp_text,
                is_mock=self.is_mock,
            )

            print(f"  -> 判定結果: 【ランク {eval_result.rank}】 (スコア: {eval_result.score})")
            print(f"  -> 一言サマリー: {eval_result.one_line_summary}")

            # DB保存
            product_dict = {
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
            self.db.save_product(product_dict)
            self.db.save_evaluation(p.id, eval_result.model_dump(), today_str)

        # 5. レポート生成
        print("\n[Step 5/5] レポートおよびダッシュボード生成中...")
        today_evaluations = self.db.get_evaluations_by_date(today_str)
        if not today_evaluations:
            today_evaluations = self.db.get_all_recent_evaluations(limit=20)

        # Markdown レポート
        md_file = self.md_reporter.generate_daily_report(today_evaluations, today_str)
        print(f"  -> Markdown レポート出力: {md_file}")

        # HTML ダッシュボード
        all_recent = self.db.get_all_recent_evaluations(limit=50)
        html_file = self.html_reporter.generate_dashboard(all_recent, today_str)
        print(f"  -> HTML ダッシュボード更新: {html_file}")
        print(f"  -> GitHub Pages用ファイル更新: {self.html_reporter.docs_output_path}")

        # GitHub への自動アップロード (設定時のみ)
        if self.github_uploader.token and self.github_uploader.repo:
            print("\n[Step 5b] GitHub Pagesへ自動アップロード中...")
            self.github_uploader.upload_file(
                file_path=html_file,
                target_path="index.html",
                commit_message=f"Update daily dashboard: {today_str}",
            )

        print("\n==================================================")
        print(f"🎉 日次パイプライン完了！")
        print(f"Obsidianノート: {md_file.name}")
        print(f"ダッシュボード: {html_file.name}")
        print("==================================================")

