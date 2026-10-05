import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from jinja2 import Template
from config import (
    BASE_DIR,
    DASHBOARD_FILE,
    DASHBOARD_PASSWORD,
    DASHBOARD_MEMBER_PASSWORD,
    DOCS_INDEX_FILE,
    TEMPLATES_DIR,
)


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
    def sanitize_url(url: Optional[str]) -> str:
        """URLが有効なHTTP/HTTPSスキームであることを確認し、それ以外は空文字を返却（XSS防止）"""
        if not url or not isinstance(url, str):
            return ""
        clean = url.strip()
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        return ""

    @staticmethod
    def encrypt_data_multirole(
        plain_text: str,
        admin_password: str,
        member_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """マルチロール対応エンベロープ暗号化 (PBKDF2 + AES-256-GCM)
        データ本体はMaster DEK (32バイト) で暗号化し、
        DEKを管理者用・メンバー用の各パスワードで個別に暗号化してパケット化する。
        """
        # 1. Master DEK (Data Encryption Key: 256bit) の生成
        dek = AESGCM.generate_key(bit_length=256)
        aesgcm_data = AESGCM(dek)
        iv_data = os.urandom(12)
        ciphertext_data = aesgcm_data.encrypt(iv_data, plain_text.encode("utf-8"), None)

        packets = []
        passwords = [("admin", admin_password)]
        if member_password:
            passwords.append(("member", member_password))

        for role, pwd in passwords:
            if not pwd:
                continue
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            derived_key = kdf.derive(pwd.encode("utf-8"))
            aesgcm_key = AESGCM(derived_key)
            iv_key = os.urandom(12)
            encrypted_dek = aesgcm_key.encrypt(iv_key, dek, None)

            packets.append({
                "role": role,
                "salt": base64.b64encode(salt).decode("utf-8"),
                "iv": base64.b64encode(iv_key).decode("utf-8"),
                "key": base64.b64encode(encrypted_dek).decode("utf-8"),
            })

        return {
            "version": "2",
            "packets": packets,
            "iv": base64.b64encode(iv_data).decode("utf-8"),
            "data": base64.b64encode(ciphertext_data).decode("utf-8"),
        }

    def generate_dashboard(
        self,
        items: List[Dict[str, Any]],
        report_date: str,
        password: Optional[str] = None,
        member_password: Optional[str] = None,
        allow_unencrypted: bool = False,
    ) -> Path:
        """インタラクティブHTMLダッシュボードを生成（マルチロールパスワード暗号化対応）"""
        admin_pass = (password if password is not None else DASHBOARD_PASSWORD) or ""
        member_pass = (member_password if member_password is not None else DASHBOARD_MEMBER_PASSWORD) or ""

        if not allow_unencrypted:
            if not admin_pass:
                raise ValueError(
                    "[Security Error] DASHBOARD_PASSWORD（管理者用合言葉）が未設定です。"
                    "平文でのデータ公開を防止するためダッシュボード生成を中断します。"
                    "環境変数または引数で合言葉を設定してください。"
                )
            if not member_pass:
                raise ValueError(
                    "[Security Error] DASHBOARD_MEMBER_PASSWORD（会員用合言葉）が未設定です。"
                    "会員向け暗号化パケットを生成できないためダッシュボード生成を中断します。"
                    "環境変数または引数で会員用合言葉を設定してください。"
                )
            if admin_pass == member_pass:
                raise ValueError(
                    "[Security Error] 管理者合言葉と会員合言葉に同一の文字列が設定されています。"
                    "ロール権限の分離が無効化されるため、異なる合言葉を設定してください。"
                )

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

            # 日本版の設計・アレンジポイント
            adapt_points = it.get("adapt_points")
            if not adapt_points or not isinstance(adapt_points, list):
                adapt_points = [
                    "国内商習慣（稟議フロー・請求書対応）に合わせた機能最適化",
                    "日本の主要SaaS（チャット・会計・SFA）とのAPI連携",
                    "日本語特有の文脈・商習慣に最適化したUIとサポート",
                ]

            # 元のプロダクトの日本語詳細解説
            orig_text = it.get("original_summary_ja")
            if not orig_text:
                orig_text = desc[:200] + "..." if len(desc) > 200 else desc

            item_date = it.get("analyzed_date") or it.get("first_seen_date") or report_date

            products_data.append(
                {
                    "id": it.get("product_id") or it.get("id") or name.lower().replace(" ", "-"),
                    "date": item_date,
                    "rank": rank,
                    "name": name,
                    "cat": category,
                    "tagline": tagline,
                    "url": self.sanitize_url(it.get("official_url") or ph_url),
                    "orig": orig_text,
                    "origNote": "海外最新ツールの機能概要 (日本語解説)" if it.get("original_summary_ja") else "海外公式発表より",
                    "idea": one_line or f"{name}の日本展開モデル",
                    "body": body,
                    "target": targets or ["法人営業チーム", "中小企業"],
                    "adapt": adapt_points[:3],
                    "snsDraft": it.get("sns_post_draft") or "",
                    "snsReplyDraft": it.get("sns_reply_draft") or (
                        f"🇯🇵 日本市場でのタイムマシン事業チャンス\n\n"
                        f"💡 コンセプト: {one_line}\n"
                        f"🎯 ターゲット: {target_str}\n"
                        f"🚀 勝機: {body[:120]}...\n\n"
                        f"🔗 公式サイト: {it.get('official_url') or ph_url}"
                    ) if one_line else "",
                    "signals": signals,
                    "image": self.sanitize_url(it.get("image_url")),
                }
            )

        products_json_str = json.dumps(products_data, ensure_ascii=False, indent=2)

        is_encrypted = bool(admin_pass and member_pass)
        encrypted_payload = None
        if is_encrypted:
            encrypted_payload = self.encrypt_data_multirole(products_json_str, admin_pass, member_pass)
        elif not allow_unencrypted:
            raise ValueError("[Security Error] 暗号化キーが不足しているためダッシュボード出力を拒否しました。")

        # テンプレートレンダリング
        template_text = self.template_path.read_text(encoding="utf-8")
        template = Template(template_text)
        rendered_html = template.render(
            report_date=report_date,
            is_encrypted=is_encrypted,
            encrypted_payload=json.dumps(encrypted_payload, ensure_ascii=False) if encrypted_payload else "null",
            products_json=products_json_str if allow_unencrypted else "[]",
        )

        # ローカル用とGitHub Pages (docs/index.html) の両方に出力
        self.output_path.write_text(rendered_html, encoding="utf-8")
        self.docs_output_path.parent.mkdir(parents=True, exist_ok=True)
        self.docs_output_path.write_text(rendered_html, encoding="utf-8")

        return self.output_path
