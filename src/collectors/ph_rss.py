import re
import xml.etree.ElementTree as ET
from typing import List
import requests
from bs4 import BeautifulSoup
from .base import BaseCollector, ProductItem


class ProductHuntRSSCollector(BaseCollector):
    FEED_URL = "https://www.producthunt.com/feed"

    def __init__(self, feed_url: str = FEED_URL):
        self.feed_url = feed_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/atom+xml,application/xml,text/xml;q=0.9,*/*;q=0.8",
        }

    def fetch_daily_products(self, limit: int = 10) -> List[ProductItem]:
        products: List[ProductItem] = []
        try:
            resp = requests.get(self.feed_url, headers=self.headers, timeout=15)
            resp.raise_for_status()
            content = resp.content

            # XMLパース
            root = ET.fromstring(content)
            # Atom or RSS 2.0判定
            # Atomの場合は {http://www.w3.org/2005/Atom} プレフィックス
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            entries = root.findall("atom:entry", ns)
            if not entries:
                entries = root.findall(".//item")

            for entry in entries[:limit]:
                title_elem = entry.find("atom:title", ns)
                if title_elem is None:
                    title_elem = entry.find("title")
                title_raw = title_elem.text if title_elem is not None and title_elem.text else ""

                # タイトルとタグラインの分割 (例: "Product Name - Tagline description")
                name = title_raw
                tagline = ""
                if " - " in title_raw:
                    parts = title_raw.split(" - ", 1)
                    name = parts[0].strip()
                    tagline = parts[1].strip()

                # リンク取得
                link_elem = entry.find("atom:link", ns)
                if link_elem is not None:
                    link = link_elem.attrib.get("href", "")
                else:
                    item_link = entry.find("link")
                    link = item_link.text if item_link is not None and item_link.text else ""

                # クエリパラメータ等の除去 (clean URL)
                clean_url = link.split("?")[0] if link else ""

                # ID抽出 (URLの末尾スラッグ)
                slug_match = re.search(r"/posts/([^/?#]+)", clean_url)
                product_id = slug_match.group(1) if slug_match else re.sub(r"[^a-zA-Z0-9_-]", "", name.lower())

                # 詳細説明・タグライン・外部リンクの抽出
                content_elem = entry.find("atom:content", ns)
                if content_elem is None:
                    content_elem = entry.find("atom:summary", ns) or entry.find("description")

                raw_content = content_elem.text if content_elem is not None and content_elem.text else ""
                official_url = None

                if raw_content:
                    soup = BeautifulSoup(raw_content, "html.parser")
                    # 各パラグラフ
                    p_tags = soup.find_all("p")
                    if p_tags:
                        first_p = p_tags[0].get_text(separator=" ").strip()
                        if first_p:
                            tagline = first_p
                            clean_desc = first_p

                    # 公式直通リンク (例: <a href=".../r/p/...">Link</a>)
                    link_a = soup.find("a", string=re.compile(r"Link", re.I))
                    if link_a and link_a.get("href"):
                        official_url = link_a["href"]

                    if not clean_desc:
                        clean_desc = soup.get_text(separator=" ").strip()
                else:
                    clean_desc = ""

                if not tagline and clean_desc:
                    tagline = clean_desc[:120]

                products.append(
                    ProductItem(
                        id=product_id,
                        name=name,
                        tagline=tagline,
                        description=clean_desc,
                        ph_url=clean_url or link,
                        official_url=official_url,
                        votes_count=0,
                        category="Tech / Web / AI",
                    )
                )

        except Exception as e:
            print(f"[Warning] Failed to fetch PH RSS feed: {e}")

        return products
