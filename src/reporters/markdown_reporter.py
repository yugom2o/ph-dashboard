from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from config import REPORTS_DIR


class MarkdownReporter:
    def __init__(self, output_dir: Path = REPORTS_DIR):
        self.output_dir = output_dir

    def generate_daily_report(self, items: List[Dict[str, Any]], target_date: str) -> Path:
        """日次Markdownレポートの生成"""
        total = len(items)
        s_count = sum(1 for it in items if it.get("rank") == "S")
        a_count = sum(1 for it in items if it.get("rank") == "A")
        b_count = sum(1 for it in items if it.get("rank") == "B")
        c_count = sum(1 for it in items if it.get("rank") == "C")

        md = []

        # YAML Frontmatter (Obsidian / Dataview 対応)
        md.append("---")
        md.append("type: ph-daily-report")
        md.append(f"date: {target_date}")
        md.append(f"total_analyzed: {total}")
        md.append(f"s_rank_count: {s_count}")
        md.append(f"a_rank_count: {a_count}")
        md.append(f"b_rank_count: {b_count}")
        md.append(f"c_rank_count: {c_count}")
        md.append("tags:")
        md.append("  - producthunt")
        md.append("  - timemachine-business")
        md.append("  - market-analysis")
        md.append("---")
        md.append("")

        # ヘッダー
        md.append("# 🚀 Product Hunt デイリー分析レポート: 日本版タイムマシン事業機会")
        md.append(f"**収集日**: {target_date}  ")
        md.append(f"**分析プロダクト数**: {total} 件  ")
        md.append(
            f"**有望判定サマリー**: 【Sランク (即検討)】{s_count}件 / "
            f"【Aランク (有望・要アレンジ)】{a_count}件 / "
            f"【Bランク (要検証)】{b_count}件 / "
            f"【Cランク (見送り)】{c_count}件"
        )
        md.append("")
        md.append("---")
        md.append("")

        # 一覧サマリーテーブル
        md.append("## 📊 本日の注目プロダクト & 日本市場判定サマリー")
        md.append("")
        md.append("| ランク | スコア | プロダクト | 元のタグライン | 日本市場での一言判定 | 想定アレンジ / 収益モデル |")
        md.append("| :---: | :---: | :--- | :--- | :--- | :--- |")
        for it in items:
            rank = it.get("rank", "-")
            score = it.get("score", 0)
            name = it.get("name", "")
            tagline = it.get("tagline", "").replace("|", "/")
            one_line = it.get("one_line_summary", "").replace("|", "/")
            pricing = it.get("pricing_model", "").replace("|", "/")
            md.append(f"| **{rank}** | {score} | **{name}** | {tagline} | {one_line} | {pricing} |")
        md.append("")
        md.append("---")
        md.append("")

        # 詳細深掘りセクション
        md.append("## 🔍 詳細分析カード (各プロダクトの深掘り)")
        md.append("")

        for idx, it in enumerate(items, start=1):
            rank = it.get("rank", "C")
            score = it.get("score", 0)
            name = it.get("name", "")
            tagline = it.get("tagline", "")
            desc = it.get("description", "")
            ph_url = it.get("ph_url", "")
            official_url = it.get("official_url", "")

            orig_ja = it.get("original_summary_ja")
            md.append(f"### {idx}. 【ランク {rank} (スコア: {score})】{name}")
            md.append(f"> **キャッチコピー**: {tagline}  ")
            if orig_ja:
                md.append(f"> **元プロダクト詳細 (日本語)**: {orig_ja}  ")
            elif desc:
                md.append(f"> **概要**: {desc[:300]}...  ")
            md.append(f"> **リンク**: [Product Hunt]({ph_url})" + (f" | [公式サイト]({official_url})" if official_url else ""))
            md.append("")

            md.append(f"* **💡 日本市場でのペイン・背景**:")
            md.append(f"  * {it.get('jp_needs', '調査中')}")
            md.append("")

            md.append(f"* **⚔️ 日本の既存競合・代替ツール**:")
            competitors = it.get("jp_competitors", [])
            if isinstance(competitors, list) and competitors:
                for comp in competitors:
                    if isinstance(comp, dict):
                        c_name = comp.get("name", "")
                        c_desc = comp.get("description", "")
                        c_diff = comp.get("differentiation", "")
                        md.append(f"  * **{c_name}**: {c_desc}（差別化: {c_diff}）")
                    else:
                        md.append(f"  * {comp}")
            else:
                comp_text = it.get("jp_competitors_text", "特筆すべき直接競合は未開拓または独自路線")
                md.append(f"  * {comp_text}")
            md.append("")

            md.append(f"* **🇯🇵 日本版ローカライズ・ビジネスアイデア**:")
            md.append(f"  * **コンセプト**: **{it.get('one_line_summary', '未定義')}**")
            md.append(f"  * **想定ターゲット**: {it.get('target_market', '中小企業・B2B')}")
            md.append(f"  * **事業化具体像**: {it.get('jp_adaptation', '国内商習慣に即したUIとテンプレート')}")
            
            adapt_pts = it.get("adapt_points")
            if isinstance(adapt_pts, list) and adapt_pts:
                md.append("  * **日本版の必須機能・設計ポイント**:")
                for pt in adapt_pts:
                    md.append(f"    - {pt}")
            md.append(f"  * **参入障壁・配慮事項**: {it.get('jp_barriers', '法規制および日本語コミュニケーション対応')}")
            md.append("")

            md.append(f"* **💰 想定マネタイズ・価格帯**: {it.get('pricing_model', '要検討')}")
            md.append(f"* **🎯 推奨アクション**: {it.get('recommendation', '要検証')}")
            md.append("")
            md.append("---")
            md.append("")

        file_path = self.output_dir / f"{target_date}_ProductHunt日次分析レポート.md"
        file_path.write_text("\n".join(md), encoding="utf-8")
        return file_path
