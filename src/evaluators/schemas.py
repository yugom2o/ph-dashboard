from typing import List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class CompetitorItem(BaseModel):
    name: str = Field(..., description="日本国内の実在する競合サービス名または企業名")
    description: str = Field(..., description="競合のサービス概要・特徴")
    differentiation: str = Field(..., description="本プロダクトとの違い・差別化ポイント")
    url: Optional[str] = Field(default=None, description="競合の公式サイトURL（確認可能な場合）")


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
    sns_post_draft: Optional[str] = Field(
        default=None,
        description="SNS（X / Threads）発信用親ポスト案（120〜180字程度。強力なフック・ツールの核心価値・ハッシュタグを含む。アルゴリズム対策のため外部リンクは含めない。※特定媒体名は伏せ『海外で話題の最新ツール』等と表現すること）",
    )
    sns_reply_draft: Optional[str] = Field(
        default=None,
        description="SNSツリー2通目用リプライ案（120〜220字程度。日本市場での具体的なタイムマシン事業の勝機・想定ターゲット・アレンジ案・国内連携ツールを提示。※外部リンク導線はシステム側で自動付与）",
    )

    @model_validator(mode="after")
    def sync_rank_with_score(self):
        """スコアとランクの整合性をコード側で強制同期（S: >=85, A: 70-84, B: 50-69, C: <50）"""
        if self.score >= 85:
            self.rank = "S"
        elif self.score >= 70:
            self.rank = "A"
        elif self.score >= 50:
            self.rank = "B"
        else:
            self.rank = "C"
        return self
