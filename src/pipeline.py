from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
from typing import Any, Dict, List, Optional
from config import (
    DAILY_FETCH_LIMIT,
    PRODUCTHUNT_TOKEN,
    THREADS_AUTO_PUBLISH,
    THREADS_ENABLE_THREAD_REPLY,
    THREADS_MAX_DAILY_POSTS,
)
from src.collectors import ProductHuntAPICollector, ProductHuntRSSCollector
from src.enrichers import LPScraper
from src.evaluators import GeminiEvaluator
from src.notifiers import WebhookNotifier
from src.publishers import ThreadsPublisher
from src.reporters import HTMLReporter, MarkdownReporter
from src.reporters.github_uploader import GitHubUploader
from src.storage import Database


class DailyPipeline:
    def __init__(self, is_mock: bool = False, force: bool = False):
        self.is_mock = is_mock
        self.force = force
        if is_mock:
            # モック実行時は専用の分離DB・出力先を使用（本番DB・成果物の汚染防止: R5対応）
            from config import BASE_DIR, DATA_DIR, REPORTS_DIR
            mock_db_path = DATA_DIR / "mock_history.db"
            mock_scratch_dir = BASE_DIR / "scratch"
            mock_scratch_dir.mkdir(parents=True, exist_ok=True)
            self.db = Database(db_path=mock_db_path)
            self.md_reporter = MarkdownReporter(output_dir=REPORTS_DIR / "mock")
            self.html_reporter = HTMLReporter(
                output_path=mock_scratch_dir / "dashboard_mock.html",
                docs_output_path=mock_scratch_dir / "index_mock.html",
            )
        else:
            self.db = Database()
            self.md_reporter = MarkdownReporter()
            self.html_reporter = HTMLReporter()

        self.enricher = LPScraper()
        self.evaluator = GeminiEvaluator()
        self.github_uploader = GitHubUploader()
        self.notifier = WebhookNotifier()
        self.threads_publisher = ThreadsPublisher()

        # コレクター選定
        if PRODUCTHUNT_TOKEN and not is_mock:
            self.collector = ProductHuntAPICollector(PRODUCTHUNT_TOKEN)
        else:
            self.collector = ProductHuntRSSCollector()

    def run(
        self,
        limit: Optional[int] = None,
        target_date: Optional[str] = None,
        publish_threads: Optional[bool] = None,
    ):
        fetch_limit = limit or DAILY_FETCH_LIMIT
        today_str = target_date or datetime.now(JST).strftime("%Y-%m-%d")

        print(f"==================================================")
        print(f"🌐 Global Tech Radar 日次分析パイプライン開始: {today_str}")
        print(f"モード: {'モック (テスト)' if self.is_mock else '本番実行 (Gemini LP解析)'} / 上限: {fetch_limit}件")
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
                    image_url="https://ph-files.imgix.net/0f6cfaa5-0557-4e08-a5d1-ac7963dd2b58.png?auto=format&format=jpeg&fit=crop&frame=1&h=512&w=1024",
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
                    image_url="https://ph-files.imgix.net/a3ccaa67-e5b0-4d5c-9e25-add309cc6b3d.png?auto=format&format=jpeg&fit=crop&frame=1&h=512&w=1024",
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
                    image_url="https://ph-files.imgix.net/424c9e7a-eb3d-4b60-b8d0-4f512096dd1e.webp?auto=format&format=jpeg&fit=crop&frame=1&h=512&w=1024",
                ),
            ][:fetch_limit]
        else:
            products = self.collector.fetch_daily_products(limit=fetch_limit)
            # APIトークン無効などで取得0件の場合、RSSコレクターへ自動フォールバック
            if not products and isinstance(self.collector, ProductHuntAPICollector):
                print("[Info] Product Hunt API取得に失敗したため、公式RSSフィードへ自動フォールバックします...")
                fallback_collector = ProductHuntRSSCollector()
                products = fallback_collector.fetch_daily_products(limit=fetch_limit)

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

            # 公式サイトURLの正規化（Product HuntリダイレクトURLの解決）
            if p.official_url:
                p.official_url = self.enricher.resolve_official_url(p.official_url)

            # アイキャッチ・OGP画像の抽出 (Product Huntページ または 公式サイト)
            if not p.image_url and not self.is_mock:
                print(f"  アイキャッチ画像を抽出中...")
                if p.ph_url:
                    p.image_url = self.enricher.fetch_og_image(p.ph_url)
                if not p.image_url and p.official_url:
                    p.image_url = self.enricher.fetch_og_image(p.official_url)
                if p.image_url:
                    print(f"  -> 画像URL取得成功: {p.image_url[:80]}...")

            lp_text = ""
            if p.official_url and not self.is_mock:
                print(f"  公式サイトをクロール中: {p.official_url}")
                lp_text = self.enricher.fetch_lp_text(p.official_url) or ""
                if lp_text:
                    print(f"  -> LPテキスト抽出成功: {len(lp_text)}文字")

            print("  AI評価中 (LP解析 + 日本市場事業性判定)...")
            eval_result = self.evaluator.evaluate(
                product_name=p.name,
                tagline=p.tagline,
                description=p.description,
                lp_text=lp_text,
                is_mock=self.is_mock,
            )

            if not eval_result:
                print(f"  -> [Warning] '{p.name}' のAI評価に失敗したためスキップします。")
                continue

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
                "image_url": p.image_url,
                "first_seen_date": today_str,
            }
            actual_product_id = self.db.save_product(product_dict)
            product_dict["id"] = actual_product_id
            self.db.save_evaluation(actual_product_id, eval_result.model_dump(), today_str)

            # Sランクまたはスコア85以上の場合は即時アラート送信
            if eval_result.rank == "S" or eval_result.score >= 85:
                alert_item = {**product_dict, **eval_result.model_dump()}
                if self.notifier.is_configured and not self.is_mock:
                    print("  -> 🎯 高スコア注目案件のためWebhookアラートを送信中...")
                    self.notifier.send_high_score_alert(alert_item)

        # 5. レポート生成
        print("\n[Step 5/5] レポートおよびダッシュボード生成中...")
        today_evaluations = self.db.get_evaluations_by_date(today_str)

        # Markdown レポート
        md_file = self.md_reporter.generate_daily_report(today_evaluations, today_str)
        print(f"  -> Markdown レポート出力: {md_file}")

        # HTML ダッシュボード (日本語詳細解説がある高品質データのみ抽出)
        all_recent = self.db.get_all_recent_evaluations(limit=100)
        valid_recent = [it for it in all_recent if it.get("original_summary_ja")]
        if not valid_recent:
            valid_recent = all_recent
        html_file = self.html_reporter.generate_dashboard(valid_recent, today_str)
        print(f"  -> HTML ダッシュボード更新: {html_file}")

        print(f"  -> GitHub Pages用ファイル更新: {self.html_reporter.docs_output_path}")

        # Webhook日次完了サマリー通知
        if self.notifier.is_configured and not self.is_mock:
            s_cnt = sum(1 for it in today_evaluations if it.get("rank") == "S")
            a_cnt = sum(1 for it in today_evaluations if it.get("rank") == "A")
            top_sorted = sorted(today_evaluations, key=lambda x: x.get("score", 0), reverse=True)
            self.notifier.send_daily_summary(
                report_date=today_str,
                total=len(today_evaluations),
                s_count=s_cnt,
                a_count=a_cnt,
                top_items=top_sorted,
            )

        # GitHub への自動アップロード (設定時 & 非モック時のみ: R5対応)
        if self.github_uploader.token and self.github_uploader.repo and not self.is_mock:
            print("\n[Step 5b] GitHub Pagesへ自動アップロード中...")
            self.github_uploader.upload_file(
                file_path=html_file,
                target_path="dashboard.html",
                commit_message=f"Update daily dashboard: {today_str}",
            )
            self.github_uploader.upload_file(
                file_path=html_file,
                target_path="index.html",
                commit_message=f"Update daily dashboard: {today_str}",
            )
            import os
            if not os.getenv("GITHUB_ACTIONS"):
                # Pagesのデプロイのみをトリガー（daily_analyzer.ymlを誤実行してThreads二重投稿するのを防止）
                self.github_uploader.trigger_workflow_dispatch("deploy_pages.yml")

        # 6. Threads への自動投稿 (有効時)
        should_publish_threads = (
            publish_threads if publish_threads is not None else THREADS_AUTO_PUBLISH
        )
        if should_publish_threads:
            print("\n[Step 6] Threadsへの自動投稿を処理中...")
            if not self.threads_publisher.is_configured:
                print("  [Skip] THREADS_ACCESS_TOKEN が未設定のためスキップします。")
            elif self.is_mock:
                print("  [Mock] モックモードのためThreads投稿をシミュレート（API呼び出しはスキップ）")
            else:
                self._publish_top_product_to_threads(today_evaluations)

        print("\n==================================================")
        print(f"🎉 日次パイプライン完了！")
        print(f"Obsidianノート: {md_file.name}")
        print(f"ダッシュボード: {html_file.name}")
        print("==================================================")

    def _publish_top_product_to_threads(self, evaluations: List[Dict[str, Any]], target_date: Optional[str] = None):
        """本日最も有望なプロダクトをThreadsに自動投稿（上限チェック＆新着0件時は未投稿の過去有望案件にフォールバック）"""
        from datetime import timezone, timedelta
        # 投稿枠判定は、分析対象日（--date）ではなく実行時点のJST現在日を常に基準とする（R3対応）
        current_jst_date = target_date or datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
        today_posted = self.db.get_threads_posts_count_by_date(current_jst_date)
        if today_posted >= THREADS_MAX_DAILY_POSTS:
            print(f"  [Skip] 本日（{current_jst_date} JST）のThreads投稿上限（{THREADS_MAX_DAILY_POSTS}件/日、本日投稿実績: {today_posted}件）に達しているためスキップします。")
            return

        # Sランク優先、次にAランク、スコア降順
        rank_order = {"S": 1, "A": 2, "B": 3, "C": 4}
        candidates = sorted(
            evaluations,
            key=lambda x: (rank_order.get(x.get("rank", "C"), 5), -x.get("score", 0)),
        )

        # 本日の未投稿・S/Aランク案件を抽出
        eligible_candidates = [
            item for item in candidates
            if item.get("rank") in ["S", "A"]
            and not self.db.is_already_posted_to_threads(item.get("product_id") or item.get("id", ""))
        ]

        # 本日の対象案件がない場合、過去の未投稿・高スコア案件からフォールバック選定（ユーザー承認仕様）
        if not eligible_candidates:
            print("  [Info] 本日の新規評価に対象案件（未投稿のS/Aランク）がないため、過去の未投稿・高スコア案件から選定します...")
            eligible_candidates = self.db.get_unposted_high_scoring_evaluations(limit=5)

        if not eligible_candidates:
            print("  [Info] 投稿対象となる未投稿のS/Aランクプロダクトがありませんでした。")
            return

        posted_count = 0
        for item in eligible_candidates:
            if posted_count >= (THREADS_MAX_DAILY_POSTS - today_posted):
                break

            p_id = item.get("product_id") or item.get("id")
            if not p_id:
                continue

            # 既に投稿済みならスキップ（念のための二重確認）
            if self.db.is_already_posted_to_threads(p_id):
                continue

            draft = item.get("sns_post_draft")
            if not draft:
                continue

            official_url = item.get("official_url")
            image_url = item.get("image_url")

            # 1通目（親ポスト）: フック＋ツールの核心＋画像
            post1_text = draft
            if "🔗" in post1_text:
                post1_text = post1_text.split("🔗")[0].strip()
            elif official_url and official_url in post1_text:
                post1_text = post1_text.replace(official_url, "").strip()

            # 2通目（リプライ）: 日本市場での勝機＋ターゲット＋公式リンク
            post2_text = None
            if THREADS_ENABLE_THREAD_REPLY:
                reply_draft = item.get("sns_reply_draft")
                if reply_draft:
                    post2_text = reply_draft
                else:
                    one_line = item.get("one_line_summary", "")
                    post2_text = (
                        f"🇯🇵 日本市場での着眼点：\n"
                        f"{one_line}\n\n"
                        f"👉 日本版MVPの具体的な機能要件・想定ARR試算は、プロフィール欄のnote週刊レポートにて徹底解剖しています📝"
                    )

                if official_url and official_url not in post2_text:
                    post2_text += f"\n\n🔗 海外公式サイト: {official_url}"

            print(f"  -> Threadsへ投稿中: 【ランク {item.get('rank')}】{item.get('name')} (画像: {'あり' if image_url else 'なし'} / ツリーリプライ: {'有効' if post2_text else '無効'}) ...")
            # Step 1: 外部API呼び出し前に原子的に予約・枠確保 (二重投稿・結果不明時の再送防止: 第3回指摘2対応)
            record_id = self.db.reserve_threads_post(
                product_id=p_id,
                text=post1_text,
                image_url=image_url,
            )

            # Step 2: 親ポストの外部公開呼び出し
            parent_id = None
            try:
                parent_id = self.threads_publisher.publish(text=post1_text, image_url=image_url)
            except Exception as e:
                print(f"  -> [Error] Threads親ポスト公開中に例外発生: {e}")
                self.db.update_threads_post_unknown(record_id, error_msg=str(e))
                print(f"  -> [Safety Guard] 結果不明（status='unknown'）として記録しました。二重投稿防止のため自動再送・別案件送信を停止します。")
                break

            if not parent_id:
                print(f"  -> [Error] 親ポストの応答IDが得られませんでした（タイムアウトまたはAPIエラー）。")
                self.db.update_threads_post_unknown(record_id, error_msg="Timeout or None response from API")
                print(f"  -> [Safety Guard] 結果不明（status='unknown'）として記録しました。二重投稿防止のため自動再送・別案件送信を停止します。")
                break

            # Step 3: 親投稿成功を即時DB更新
            self.db.update_threads_post_success(record_id=record_id, post_id=parent_id)
            posted_count += 1
            print(f"  -> 🎉 Threads親ポスト公開成功！ (親Post ID: {parent_id})")

            # Step 4: リプライ（子ポスト）を投稿
            if post2_text:
                import time
                print("  -> 親ポスト反映待ち (4秒待機後、2通目リプライを自動投稿)...")
                time.sleep(4)
                reply_id = self.threads_publisher.publish_reply(parent_post_id=parent_id, text=post2_text)
                if reply_id:
                    self.db.update_threads_post_reply(
                        record_id=record_id,
                        reply_post_id=reply_id,
                        reply_text=post2_text,
                    )
                    print(f"  -> 🎉 Threadsリプライ公開成功！ (リプライID: {reply_id})")
                else:
                    print(f"  -> [Warning] 親ポストは公開されましたが、リプライの公開に失敗しました (親Post ID: {parent_id})。")

        if posted_count == 0 and today_posted == 0:
            print("  [Info] 本日は新規投稿対象（未投稿のS/Aランクプロダクト）がありませんでした。")


