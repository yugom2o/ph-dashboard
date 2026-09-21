from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CompetitorItem(BaseModel):
    name: str = Field(..., description="日本国内の競合サービス名または企業名")
    description: str = Field(..., description="競合のサービス概要・特徴")
    differentiation: str = Field(..., description="本プロダクトとの違い・差別化ポイント")


class EvaluationResult(BaseModel):
    rank: Literal["S", "A", "B", "C"] = Field(
        ...,
        description="日本市場成立度ランク: S (即参入検討) / A (有望・要アレンジ) / B (ニッチ/要検証) / C (不適・見送り)",
    )
    score: int = Field(..., ge=0, le=100, description="成立可能性スコア (0〜100点)")
    one_line_summary: str = Field(..., description="日本市場向けの一言サマリー (例: 日本のB2B営業向けスライド自動生成SaaS)")
    target_market: str = Field(..., description="想定ターゲット (例: 中小企業の広報・マーケティング担当者)")
    pricing_model: str = Field(..., description="日本版での想定収益モデル・価格帯 (例: 月額3万〜5万円のB2B SaaS)")
    jp_needs: str = Field(..., description="日本国内での課題・ペイン・需要の背景")
    jp_competitors: List[CompetitorItem] = Field(
        default_factory=list,
        description="日本国内に既に存在する類似サービス・代替ツールと競合比較",
    )
    jp_barriers: str = Field(..., description="日本特有の参入障壁、法規制、商習慣、文化・言語の壁")
    jp_adaptation: str = Field(..., description="日本市場向けにローカライズ・アレンジする場合の具体的なプロダクト案")
    recommendation: str = Field(..., description="結論と推奨アクション (例: 個人開発またはスタートアップが参入すべきか)")
