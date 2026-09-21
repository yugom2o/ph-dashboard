import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jinja2 import Template
from config import BASE_DIR, DASHBOARD_FILE, DASHBOARD_PASSWORD, DOCS_INDEX_FILE, TEMPLATES_DIR


class HTMLReporter:
    def __init__(
        self,
        template_path: Path = TEMPLATES_DIR / "dashboard_template.html",
        output_path: Path = DASHBOARD_FILE,
        docs_output_path: Path = DOCS_INDEX_FILE,
    ):
        self.template_path = template_path
        self.output_path = output_path
        self.docs_output_path = docs_output_path

    @staticmethod
    def encrypt_data(plain_text: str, password: str) -> Dict[str, str]:
        """PBKDF2 + AES-256-GCM でデータを暗号化 (ブラウザのWebCrypto APIと完全互換)"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode("utf-8"))
        aesgcm = AESGCM(key)
        iv = os.urandom(12)
        ciphertext = aesgcm.encrypt(iv, plain_text.encode("utf-8"), None)

        return {
            "salt": base64.b64encode(salt).decode("utf-8"),
            "iv": base64.b64encode(iv).decode("utf-8"),
            "data": base64.b64encode(ciphertext).decode("utf-8"),
        }

    def generate_dashboard(
        self,
        items: List[Dict[str, Any]],
        report_date: str,
        password: Optional[str] = None,
    ) -> Path:
        """インタラクティブHTMLダッシュボードを生成（パスワード暗号化対応）"""
        pass_to_use = password if password is not None else DASHBOARD_PASSWORD
        products_data = []

        for it in items:
            rank = it.get("rank", "C")
            score = it.get("score", 0)
            name = it.get("name", "")
            tagline = it.get("tagline", "")
            desc = it.get("description", "")
            ph_url = it.get("ph_url", "")
            category = it.get("category", "Tech / Web")
            one_line = it.get("one_line_summary", "")
            body = it.get("jp_adaptation", "")
            target_str = it.get("target_market", "国内法人 / 中小企業")
            targets = [t.strip() for t in target_str.replace("、", ",").split(",") if t.strip()][:3]

            # 競合情報の要約
            competitors = it.get("jp_competitors", [])
            comp_summary = ""
            if isinstance(competitors, list) and competitors:
                comp_names = []
                for c in competitors:
                    if isinstance(c, dict):
                        comp_names.append(c.get("name", ""))
                    elif isinstance(c, str):
                        comp_names.append(c)
                comp_summary = "、".join(comp_names[:3])
            elif isinstance(competitors, str) and competitors:
                try:
                    c_json = json.loads(competitors)
                    comp_names = [c.get("name", "") for c in c_json if isinstance(c, dict)]
                    comp_summary = "、".join(comp_names[:3])
                except Exception:
                    comp_summary = competitors[:50]

            # シグナル
            signals = [
                {
                    "k": "国内ペイン",
                    "v": "極めて高い" if score >= 85 else ("高い" if score >= 70 else "要検証"),
                    "t": "good" if score >= 70 else "mid",
                    "n": it.get("jp_needs", "")[:120],
                },
                {
                    "k": "国内競合",
                    "v": comp_summary if comp_summary else "先行余地あり",
                    "t": "mid" if comp_summary else "good",
                    "n": "競合状況: " + (comp_summary or "直接の類似SaaSは限定的"),
                },
                {
                    "k": "参入障壁",
                    "v": "要商習慣適合" if "法規制" in it.get("jp_barriers", "") else "低〜中",
                    "t": "good" if score >= 80 else "mid",
                    "n": it.get("jp_barriers", "")[:120],
                },
                {
                    "k": "想定価格",
                    "v": it.get("pricing_model", "月額サブスクリプション")[:25],
                },
            ]

            adapt_points = [
                "国内の商習慣・稟議フローに合わせた機能最適化",
                "日本語による高品質なUI/UXと顧客サポートの提供",
                "国内の既存ツール（SFA、会計、チャット等）とのAPI連携",
            ]

            products_data.append(
                {
                    "id": it.get("product_id") or it.get("id") or name.lower().replace(" ", "-"),
                    "rank": rank,
                    "name": name,
                    "cat": category,
                    "tagline": tagline,
                    "url": ph_url,
                    "orig": desc[:150] + "..." if len(desc) > 150 else desc,
                    "origNote": "Product Hunt掲載情報より",
                    "idea": one_line or f"日本版 {name}",
                    "body": body,
                    "target": targets or ["法人営業チーム", "中小企業"],
                    "adapt": adapt_points,
                    "signals": signals,
                }
            )

        products_json_str = json.dumps(products_data, ensure_ascii=False, indent=2)

        is_encrypted = bool(pass_to_use)
        encrypted_payload = None
        if is_encrypted:
            encrypted_payload = self.encrypt_data(products_json_str, pass_to_use)

        # テンプレートレンダリング
        template_text = self.template_path.read_text(encoding="utf-8")
        template = Template(template_text)
        rendered_html = template.render(
            report_date=report_date,
            is_encrypted=is_encrypted,
            encrypted_payload=json.dumps(encrypted_payload, ensure_ascii=False) if encrypted_payload else "null",
            products_json=products_json_str if not is_encrypted else "[]",
        )

        # ローカル用とGitHub Pages (docs/index.html) の両方に出力
        self.output_path.write_text(rendered_html, encoding="utf-8")
        self.docs_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.docs_output_path.write_text(rendered_html, encoding="utf-8")

        return self.output_path
