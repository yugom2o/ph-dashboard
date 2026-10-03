import json
from typing import Any, Dict, List, Optional
import requests
from config import WEBHOOK_URL


class WebhookNotifier:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or WEBHOOK_URL

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url and self.webhook_url.startswith("http"))

    def send_daily_summary(
        self,
        report_date: str,
        total: int,
        s_count: int,
        a_count: int,
        top_items: List[Dict[str, Any]],
    ) -> bool:
        """日次分析完了サマリーを通知"""
        if not self.is_configured:
            return False

        lines = [
            f"🌐 **【Global Tech Radar】日次分析完了 ({report_date})**",
            f"本日分析: {total}件 | Sランク: {s_count}件 | Aランク: {a_count}件",
            "",
        ]

        if top_items:
            lines.append("🔥 **本日の注目プロダクト:**")
            for it in top_items[:3]:
                name = it.get("name", "")
                rank = it.get("rank", "-")
                score = it.get("score", 0)
                one_line = it.get("one_line_summary", "")
                official_url = it.get("official_url", "")
                link_str = f" ([公式]({official_url}))" if official_url else ""
                lines.append(f"• **[{rank} / {score}点] {name}**{link_str}")
                lines.append(f"  └ {one_line}")

        message = "\n".join(lines)
        return self._post_payload(message)

    def send_high_score_alert(self, item: Dict[str, Any]) -> bool:
        """Sランクや高スコアプロダクトを即時通知"""
        if not self.is_configured:
            return False

        name = item.get("name", "")
        rank = item.get("rank", "S")
        score = item.get("score", 0)
        tagline = item.get("tagline", "")
        one_line = item.get("one_line_summary", "")
        official_url = item.get("official_url", "")
        sns_draft = item.get("sns_post_draft", "")

        lines = [
            f"🎯 **【注目案件検知: ランク {rank} (スコア {score})】**",
            f"**プロダクト**: {name}" + (f" ({official_url})" if official_url else ""),
            f"**海外発表**: {tagline}",
            f"**日本市場での勝機**: {one_line}",
        ]

        if sns_draft:
            lines.append("")
            lines.append("📱 **SNS投稿案 (X / Threads):**")
            lines.append(f"```{sns_draft}```")

        message = "\n".join(lines)
        return self._post_payload(message)

    def _post_payload(self, text: str) -> bool:
        try:
            # Discord / Slack 共通互換ペイロード
            payload = {
                "text": text,        # Slack用
                "content": text,     # Discord用
            }
            resp = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return resp.status_code in (200, 204)
        except Exception as e:
            print(f"[Warning] Webhook通知に失敗しました: {e}")
            return False
