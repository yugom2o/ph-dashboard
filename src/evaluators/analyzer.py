import json
import re
from typing import Optional
from config import GEMINI_API_KEY, GEMINI_MODEL
from .prompts import SYSTEM_PROMPT, create_evaluation_prompt
from .schemas import CompetitorItem, EvaluationResult


class GeminiEvaluator:
    def __init__(self, api_key: Optional[str] = None, model: str = GEMINI_MODEL):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"[Warning] Failed to initialize Google GenAI client: {e}")

    def evaluate(
        self,
        product_name: str,
        tagline: str,
        description: str,
        lp_text: str = "",
        is_mock: bool = False,
    ) -> EvaluationResult:
        """プロダクトを評価してEvaluationResultを返却"""
        if is_mock or not self.client:
            return self._generate_mock_evaluation(product_name, tagline, description)

        import time
        # レートリミット (15 RPM) 防止のためのウェイト
        time.sleep(3)

        prompt = create_evaluation_prompt(product_name, tagline, description, lp_text)

        # 1. 構造化出力 (response_schema) での評価を試行
        for attempt in range(2):
            try:
                from google.genai import types

                config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=EvaluationResult,
                    temperature=0.2,
                )

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )

                res_text = response.text.strip()
                res_text = re.sub(r"^```json\s*", "", res_text)
                res_text = re.sub(r"\s*```$", "", res_text)
                return self._parse_json_safely(res_text, product_name, tagline, description)

            except Exception as e:
                err_str = str(e)
                if "429" in err_str and attempt == 0:
                    print("[Info] Rate limit reached (429). Waiting 6 seconds before retry...")
                    time.sleep(6)
                    continue
                print(f"[Warning] Gemini evaluation attempt failed: {e}")
                break

        return self._generate_mock_evaluation(product_name, tagline, description)

    def _parse_json_safely(self, text: str, product_name: str, tagline: str, description: str) -> EvaluationResult:
        """JSON文字列から安全にEvaluationResultを復元"""
        try:
            return EvaluationResult.model_validate_json(text)
        except Exception:
            try:
                data = json.loads(text)
                # 万が一ルートがリストや別キーでラップされている場合の展開
                if isinstance(data, list) and data:
                    data = data[0]
                for k in ["evaluation", "result", "data", "analysis"]:
                    if k in data and isinstance(data[k], dict):
                        data = data[k]
                        break
                return EvaluationResult.model_validate(data)
            except Exception as ex:
                print(f"[Warning] Failed to parse model output as EvaluationResult: {ex}")
                return self._generate_mock_evaluation(product_name, tagline, description)

    def _generate_mock_evaluation(self, product_name: str, tagline: str, description: str) -> EvaluationResult:
        """APIキーなし・テスト実行用の高品質モック評価"""
        name_lower = (product_name + " " + tagline).lower()

        if any(w in name_lower for w in ["sales", "deck", "lead", "b2b", "crm", "proposal"]):
            return EvaluationResult(
                original_summary_ja="対象企業のWebサイトURLを入力するだけで、その企業の公開情報や事業内容をAIがクロール・解析し、商談ですぐに使える個別最適化された提案スライド（インサイトデッキ）を数分で自動作成する営業支援ツール。",
                rank="S",
                score=91,
                one_line_summary="【法人営業向け】企業URLからIR・PR TIMESを自動分析し提案スライド(PPTX)を3分で生成するSaaS",
                target_market="B2B企業の法人営業チーム、広告・PR代理店、コンサルティング会社",
                pricing_model="月額3万〜10万円 / 社 (3〜10アカウント含むシート課金)",
                jp_needs="初回商談前の企業リサーチや提案書作成に営業マンが週数時間を浪費している。既存の企業DB（SPEEDAやSalesNow）は情報閲覧にとどまり、提案書スライドへの落とし込みは属人的な手作業のまま放置されている。",
                jp_competitors=[
                    CompetitorItem(
                        name="SalesNow / SPEEDA",
                        description="国内最大級の企業情報データベースおよび営業リスト作成SaaS",
                        differentiation="企業情報の提供にとどまり、自社商材と相手課題を掛け合わせたPPTXスライド生成までは行わない点。",
                    ),
                    CompetitorItem(
                        name="イルシル (ELSILE)",
                        description="日本人向けのAIスライド自動生成サービス",
                        differentiation="汎用スライド作成ツールであり、営業先URLから課題予測を行って商談提案書を組む特化機能はない点。",
                    ),
                ],
                jp_barriers="日本企業特有の稟議・商談用スライド様式への適合、社内提案情報の機密保持セキュリティ要件。",
                jp_adaptation="PR TIMESの最新プレスリリースや適時開示情報（有価証券報告書の中期経営計画）を自動巡回。自社サービス資料を一度登録すれば、相手企業の現在の方針と自社商材をマッチングさせた日本語PowerPoint形式の提案骨子を即時出力する。",
                adapt_points=[
                    "PR TIMES・適時開示・採用ページの自動スクレイピングと課題抽出",
                    "日本の商談文化に合わせた日本語PowerPoint(PPTX)形式でのエクスポート",
                    "Sansan・Salesforce・HubSpot等の国内主要CRM/SFAとの連携",
                ],
                recommendation="即参入検討。バーティカルB2B営業SaaSとして国内PMFの確度が高く、ARR化しやすい。",
            )
        elif any(w in name_lower for w in ["video", "edit", "clip", "media", "transcribe"]):
            return EvaluationResult(
                original_summary_ja="インタビューや対談などの長尺生動画をアップロードすると、AIが発言内容の文脈を理解して見どころ・核心部分を抽出し、無駄な相槌やフィラーを削ぎ落としたラフカット（粗編集タイムライン）を自動生成する編集ツール。",
                rank="A",
                score=78,
                one_line_summary="【広報・人事向け】採用動画・顧客事例インタビュー特化の日本語テロップ＆粗編集自動化ツール",
                target_market="企業の採用人事、マーケティング・広報部門、オウンドメディア制作会社",
                pricing_model="月額2.5万〜8万円のサブスクリプション",
                jp_needs="採用動画や顧客事例インタビュー動画の需要が急増しているが、長時間の映像から重要発言を選定して切り出す作業に多大な時間と外注費がかかっている。",
                jp_competitors=[
                    CompetitorItem(
                        name="Vrew",
                        description="音声認識による自動字幕・無音カット編集ツール",
                        differentiation="カットと字幕付けが主用途であり、長尺インタビューから『文脈を読んで見どころを構成する』機能はない点。",
                    )
                ],
                jp_barriers="日本語特有の相槌（『なるほど』『えーっと』）の自然な処理と、国内特有のテロップ装飾文化への適応。",
                jp_adaptation="インタビューの想定問答アジェンダを読み込ませ、各設問のベストアンサー部分をAIが自律抽出。Premiere ProやFinal Cut Proのタイムライン形式で出力し、社内スタッフでも30分で事例動画を完成できるパッケージ。",
                adapt_points=[
                    "日本語の話し言葉に特化した相槌・フィラーの自動除去アルゴリズム",
                    "インタビューの設問リストに沿った章立て・構成の自動生成",
                    "Adobe Premiere Pro / Final Cut Pro向けXMLタイムライン書き出し",
                ],
                recommendation="有望。採用広報や導入事例動画などユースケースを絞り込むことで即座に導入が進みやすい。",
            )
        else:
            return EvaluationResult(
                original_summary_ja=f"Product Huntで注目を集める「{product_name}」は、{tagline}を実現する最新ツール。直感的なインターフェースとAIによる自動化により、従来の煩雑な作業フローを効率化しユーザー体験を向上させる。",
                rank="A",
                score=76,
                one_line_summary=f"【国内中小・チーム向け】{tagline}を日本語業務フローに直結させる業務自動化SaaS",
                target_market="国内の中小企業・フリーランス・クリエイター組織",
                pricing_model="月額1,980円〜14,800円のチーム課金モデル",
                jp_needs="少子高齢化・労働力不足に伴い、単一業務の属人化解消や直感的に扱えるデジタルツールの需要が日本国内で急速に高まっている。",
                jp_competitors=[
                    CompetitorItem(
                        name="従来型スプレッドシート運用 / 汎用SaaS",
                        description="手作業での転記や複数ツールの手動併用による運用",
                        differentiation="AIによる自動化と直感的なモダンUIにより、学習コスト不要で工数を80%削減。",
                    )
                ],
                jp_barriers="日本語UIの自然さ、国内商慣習（インボイス対応・請求書払い対応）、手厚いカスタマーサポート要求。",
                jp_adaptation="日本のビジネス現場で多用されるSlackやLINE WORKS、freeeとの連携プラグインを標準搭載し、専門知識不要で即日導入できるローカライズUIを提供する。",
                adapt_points=[
                    "Slack・LINE WORKS等の国内定番コミュニケーションツールとの連携",
                    "国内法制度・商慣習（インボイス・電帳法・稟議フロー）に準拠した設計",
                    "導入時の設定を5分で終わらせる日本語テンプレートプリセット",
                ],
                recommendation="要検証・要アレンジ。ターゲット業界を特定し、国内特有のSaaSエコシステムに組み込むことで勝算あり。",
            )
