import re
from typing import Optional
import requests
from bs4 import BeautifulSoup


class LPScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        }

    def fetch_lp_text(self, url: str, max_chars: int = 2000) -> Optional[str]:
        """プロダクト公式サイト（LP）から重要テキストを抽出"""
        if not url or not url.startswith("http"):
            return None

        # 1. Jina Reader による Markdown 抽出を試行 (高速・構造化)
        try:
            jina_url = f"https://r.jina.ai/{url}"
            resp = requests.get(jina_url, headers={"User-Agent": "ProductHuntAnalyzer/1.0"}, timeout=self.timeout)
            if resp.status_code == 200 and len(resp.text.strip()) > 100:
                text = resp.text.strip()
                # 余計なマークダウン装飾やリンクURLを少しクリーンアップ
                clean_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
                clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
                return clean_text[:max_chars]
        except Exception:
            pass

        # 2. 直接 requests + BeautifulSoup で主要要素を抽出
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "svg", "noscript"]):
                tag.decompose()

            # タイトル、メタディスクリプション
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()

            # 見出しと本文
            headings_and_p = []
            if title:
                headings_and_p.append(f"# {title}")
            if meta_desc:
                headings_and_p.append(f"> {meta_desc}")

            for elem in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                txt = elem.get_text(separator=" ").strip()
                if len(txt) > 20 and not txt.startswith("©"):
                    headings_and_p.append(txt)

            combined = "\n".join(headings_and_p)
            combined = re.sub(r"\n{3,}", "\n\n", combined).strip()
            return combined[:max_chars] if combined else None
        except Exception as e:
            print(f"[Warning] Failed to fetch LP content for {url}: {e}")
            return None
