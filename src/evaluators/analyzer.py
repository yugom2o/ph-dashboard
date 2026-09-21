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

        prompt = create_evaluation_prompt(product_name, tagline, description, lp_text)

        try:
            from google.genai import types

            # Google Search Grounding と JSONレスポンスの組み合わせ
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema=EvaluationResult,
                temperature=0.2,
            )

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )

            # JSON文字列からパース
            res_text = response.text.strip()
            # 万が一markdownコードブロックに囲まれていた場合の除去
            res_text = re.sub(r"^```json\s*", "", res_text)
            res_text = re.sub(r"\s*```$", "", res_text)
            return EvaluationResult.model_validate_json(res_text)

        except Exception as e:
            print(f"[Warning] Gemini evaluation failed with structured schema + search, trying fallback: {e}")
            return self._fallback_evaluate(prompt, product_name, tagline, description)

    def _fallback_evaluate(self, prompt: str, product_name: str, tagline: str, description: str) -> EvaluationResult:
        """Search grounding または Schema がエラーとなった場合のフォールバック評価"""
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.2,
            )
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt + "\n\n必ずスキーマに適合する純粋なJSONオブジェクトのみを出力してください。",
                config=config,
            )
            res_text = response.text.strip()
            res_text = re.sub(r"^```json\s*", "", res_text)
            res_text = re.sub(r"\s*```$", "", res_text)
            return EvaluationResult.model_validate_json(res_text)
        except Exception as ex:
            print(f"[Error] Fallback evaluation also failed: {ex}. Using mock fallback.")
            return self._generate_mock_evaluation(product_name, tagline, description)

    def _generate_mock_evaluation(self, product_name: str, tagline: str, description: str) -> EvaluationResult:
        """APIキーなし・テスト実行用の高品質モック評価"""
        # プロダクト名等から適度なバリエーションを持たせる
        name_lower = (product_name + " " + tagline).lower()

        if any(w in name_lower for w in ["sales", "deck", "lead", "b2b", "crm", "proposal"]):
            return EvaluationResult(
                rank="S",
                score=91,
                one_line_summary="日本のB2B営業向け「URLから提案スライド(PPTX)自動生成SaaS」",
                target_market="法人営業組織、広告代理店、コンサルティング会社",
                pricing_model="月額3万〜10万円 / アカウント (シート課金型B2B SaaS)",
                jp_needs="初回商談前の企業リサーチおよび提案書作成に多大な工数を要しているが、既存DBツールはデータ閲覧止まりで資料作成まで自動化できていない。",
                jp_competitors=[
                    CompetitorItem(
                        name="SalesNow / SPEEDA",
                        description="企業情報データベースおよび営業リスト作成ツール",
                        differentiation="企業データ提供に特化しており、自社商材と相手課題を組み合わせたスライド生成までは行わない点。",
                    ),
                    CompetitorItem(
                        name="イルシル (ELSILE)",
                        description="日本人向けAIスライド生成サービス",
                        differentiation="汎用スライド作成ツールであり、相手企業のURLから課題を分析して提案構成を組む特化機能はない点。",
                    ),
                ],
                jp_barriers="日本企業特有の承認（稟議）用フォーマットへの適合、社内情報の機密保持セキュリティ要件。",
                jp_adaptation="PR TIMESや適時開示情報、中期経営計画を自動解析し、日本の商談文化に馴染むPPTXテンプレートで提案骨子を出力するサービス。",
                recommendation="即参入検討。バーティカルB2B SaaSとして日本国内でのPMF難易度が低く有望。",
            )
        elif any(w in name_lower for w in ["video", "edit", "clip", "media", "transcribe"]):
            return EvaluationResult(
                rank="A",
                score=78,
                one_line_summary="採用広報・導入事例特化型「日本語テロップ＆見どころ粗編集自動化」",
                target_market="企業の採用人事、マーケティング部、オウンドメディア運用者",
                pricing_model="月額2万〜6万円のサブスクリプション",
                jp_needs="採用動画や顧客事例インタビュー動画の内製化が進む一方、長時間の映像から重要発言を切り出す作業がボトルネック。",
                jp_competitors=[
                    CompetitorItem(
                        name="Vrew",
                        description="音声認識による自動字幕・カット編集ツール",
                        differentiation="汎用の編集UIであり、文脈を理解してインタビュー動画の見どころを自律的に粗編集する機能は限定的。",
                    )
                ],
                jp_barriers="日本語特有の相槌や話し言葉の自然な要約、フォント・テロップ文化（YouTube/TikTok風装飾）への適応。",
                jp_adaptation="インタビューの設問リストに沿って章立てを自動生成し、企業ロゴや定型テロップを自動配置するパッケージ。",
                recommendation="有望。採用広報やカスタマーサクセス事例動画にユースケースを絞り込めば即効性あり。",
            )
        else:
            return EvaluationResult(
                rank="A",
                score=75,
                one_line_summary=f"日本市場向けローカライズ版 {product_name}",
                target_market="国内の中小企業・フリーランス・クリエイター",
                pricing_model="月額1,500〜9,800円のSaaSモデル",
                jp_needs="業務の属人化解消やデジタル化推進において手軽に導入できるツールの需要が高い。",
                jp_competitors=[
                    CompetitorItem(
                        name="国内の既存代替SaaS / スプレッドシート運用",
                        description="手作業または従来型業務ソフトウェアでの運用",
                        differentiation="AIによる自動化と直感的なモダンUIによる工数削減。",
                    )
                ],
                jp_barriers="日本語UIの自然さ、国内商慣習（請求書払い対応、インボイス対応等）。",
                jp_adaptation="日本のビジネスフローに合わせたプリセットテンプレートの用意と日本語サポートの提供。",
                recommendation="要アレンジ。国内ターゲットの絞り込みと特定業界向けローカライズを推奨。",
            )
