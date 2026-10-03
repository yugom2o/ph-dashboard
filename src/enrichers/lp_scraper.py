import os
import re
import shutil
import subprocess
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
import requests
from bs4 import BeautifulSoup


class LPScraper:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
        }

    @staticmethod
    def resolve_official_url(url: Optional[str]) -> Optional[str]:
        """
        Product HuntのリダイレクトURL (https://www.producthunt.com/r/...) を追跡し、
        純粋な本来の公式サイトURL（トラッキングパラメータ除去済み）を取得する
        """
        if not url or not url.startswith("http"):
            return url

        if "producthunt.com/r/" not in url:
            return url

        curl_path = shutil.which("curl")
        if not curl_path:
            return url

        try:
            # curl でリダイレクト後の最終URLを取得
            devnull = "NUL" if os.name == "nt" else "/dev/null"
            cmd = [
                curl_path,
                "-I", "-L", "-s",
                "-o", devnull,
                "-w", "%{url_effective}",
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            final_url = result.stdout.strip()

            if final_url and final_url.startswith("http") and "producthunt.com" not in final_url:
                # 追跡パラメータ (?ref=producthunt や ?utm_source=... 等) を綺麗に除去
                parsed = urlparse(final_url)
                query_params = parse_qs(parsed.query)
                clean_params = {
                    k: v for k, v in query_params.items()
                    if not k.startswith("utm_") and k not in ["ref", "source"]
                }
                clean_query = urlencode(clean_params, doseq=True)
                return urlunparse(parsed._replace(query=clean_query))
        except Exception as e:
            print(f"[Warning] 公式URLの解決中に例外が発生しました: {e}")

        return url

    def fetch_lp_text(self, url: str, max_chars: int = 2000) -> Optional[str]:
        """プロダクト公式サイト（LP）から重要テキストを抽出"""
        if not url or not url.startswith("http"):
            return None

        # リダイレクトURLの場合は本来の公式サイトURLに解決
        target_url = self.resolve_official_url(url) or url

        # 1. Jina Reader による Markdown 抽出を試行 (高速・構造化)
        try:
            jina_url = f"https://r.jina.ai/{target_url}"
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
            resp = requests.get(target_url, headers=self.headers, timeout=self.timeout)
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
            print(f"[Warning] Failed to fetch LP content for {target_url}: {e}")
            return None
