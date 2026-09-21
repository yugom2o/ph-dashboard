from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel, Field


class ProductItem(BaseModel):
    id: str = Field(..., description="一意のプロダクト識別子 (例: ph_slug または ID)")
    name: str = Field(..., description="プロダクト名")
    tagline: str = Field("", description="キャッチコピー・短文紹介")
    description: str = Field("", description="詳細説明")
    ph_url: str = Field(..., description="Product Huntの投稿URL")
    official_url: Optional[str] = Field(None, description="プロダクトの公式サイトURL")
    votes_count: int = Field(0, description="Upvote数")
    category: str = Field("", description="トピック・カテゴリ")
    lp_content: Optional[str] = Field(None, description="公式LPから抽出したテキスト")


class BaseCollector(ABC):
    @abstractmethod
    def fetch_daily_products(self, limit: int = 10) -> List[ProductItem]:
        """日次の注目プロダクト一覧を取得"""
        pass
