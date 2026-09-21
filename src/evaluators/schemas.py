from typing import List, Literal
from pydantic import BaseModel, Field


class CompetitorItem(BaseModel):
    name: str = Field(..., description="日本国内の実在する競合サービス名または企業名")
    description: str = Field(..., description="競合のサービス概要・特徴")
    differentiation: str = Field(..., description="本プロダクトとの違い・差別化ポイント")


class EvaluationResult(BaseModel):
    original_summary_ja: str = Field(
        ...,
        description="元のプロダクトの日本語による詳細解説（どんな機能があり、誰のどんな課題をどう解決するツールか。200〜300文字で具体的に記述）",
    )
    rank: Literal["S", "A", "B", "C"] = Field(
        ...,
        description="日本市場成立度ランク: S (即参入検討) / A (有望・要アレンジ) / B (ニッチ/要検証) / C (不適・見送り)",
    )
    score: int = Field(..., ge=0, le=100, description="成立可能性スコア (0〜100点)")
    one_line_summary: str = Field(
        ...,
        description="日本市場向けビジネスの見出し・キャッチコピー（※『日本版〇〇』や『ローカライズ版〇〇』のような抽象的表現は禁止！『【ターゲット×具体的提供価値】例: 企業のIRとPR TIMESから営業提案書(PPTX)を3分で自動生成するSaaS』のように具体的に書くこと）",
    )
    target_market: str = Field(..., description="日本版での明確なターゲット顧客（例: 中小企業の採用人事、Web広告代理店の運用者）")
    pricing_model: str = Field(..., description="日本版での想定課金モデルと価格帯（例: 初期10万円＋月額3万〜5万円/社）")
    jp_needs: str = Field(..., description="日本国内でのリアルな課題・ペイン・需要の背景（なぜ今日本で求められるのか）")
    jp_competitors: List[CompetitorItem] = Field(
        default_factory=list,
        description="日本国内に既に存在する類似サービス・代替ツールと差別化比較",
    )
    jp_barriers: str = Field(..., description="日本特有の参入障壁、法規制（インボイス、個人情報保護法等）、商習慣（稟議、代理店商流）")
    jp_adaptation: str = Field(
        ...,
        description="日本版ビジネスモデルの具体像（どの国内ツール・SaaSと連携するか、どんな日本語特有のワークフローに落とし込むか、業務フローのどこに組み込むかを具体的に解説）",
    )
    adapt_points: List[str] = Field(
        default_factory=list,
        description="日本市場向けに開発する際の具体的な機能・設計ポイント3選（例: ['PR TIMES・有価証券報告書の自動スクレイピング', '国内商談でそのまま使えるPowerPoint出力', 'HubSpotやSalesforce連携']）",
    )
    recommendation: str = Field(..., description="結論と推奨アクション（個人開発/スタートアップ/大企業新規事業としての参入是非）")
