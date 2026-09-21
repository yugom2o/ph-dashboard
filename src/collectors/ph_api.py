from datetime import datetime, timedelta
from typing import List, Optional
import requests
from .base import BaseCollector, ProductItem


class ProductHuntAPICollector(BaseCollector):
    GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token

    def fetch_daily_products(self, limit: int = 10) -> List[ProductItem]:
        if not self.api_token:
            print("[Info] Product Hunt API Token is not provided. Skipping API collector.")
            return []

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # 過去24時間の投稿を取得
        yesterday_iso = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

        query = """
        query GetDailyPosts($postedAfter: DateTime!, $first: Int!) {
          posts(order: VOTES, postedAfter: $postedAfter, first: $first) {
            edges {
              node {
                id
                name
                tagline
                description
                url
                website
                votesCount
                topics(first: 3) {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "postedAfter": yesterday_iso,
            "first": limit,
        }

        products: List[ProductItem] = []
        try:
            resp = requests.post(
                self.GRAPHQL_URL,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                topics = [t["node"]["name"] for t in node.get("topics", {}).get("edges", []) if "node" in t]
                category_str = ", ".join(topics) if topics else "Tech / Web / AI"

                products.append(
                    ProductItem(
                        id=str(node.get("id")),
                        name=node.get("name", ""),
                        tagline=node.get("tagline", ""),
                        description=node.get("description", ""),
                        ph_url=node.get("url", ""),
                        official_url=node.get("website"),
                        votes_count=node.get("votesCount", 0),
                        category=category_str,
                    )
                )
        except Exception as e:
            print(f"[Warning] Failed to fetch from Product Hunt GraphQL API: {e}")

        return products
