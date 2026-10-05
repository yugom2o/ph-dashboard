import re
import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.db import Database

def parse_report_file(file_path: Path):
    content = file_path.read_text(encoding="utf-8")
    date_match = re.search(r"date:\s*([\d-]+)", content) or re.search(r"(\d{4}-\d{2}-\d{2})", file_path.name)
    report_date = date_match.group(1) if date_match else "2026-10-01"

    # Split by cards
    cards = re.split(r"###\s+\d+\.\s+【ランク\s+([SABC])\s+\(スコア:\s*(\d+)\)】\s*(.+)", content)
    items = []
    
    for i in range(1, len(cards), 4):
        rank = cards[i].strip()
        score = int(cards[i+1].strip())
        name = cards[i+2].strip()
        body = cards[i+3]

        tagline_m = re.search(r">\s*\*\*キャッチコピー\*\*:\s*(.+)", body)
        tagline = tagline_m.group(1).strip() if tagline_m else ""

        orig_m = re.search(r">\s*\*\*元プロダクト詳細\s*\(日本語\)\*\*:\s*(.+)", body)
        orig = orig_m.group(1).strip() if orig_m else ""

        ph_url_m = re.search(r"\[Product Hunt\]\((https://[^\)]+)\)", body)
        ph_url = ph_url_m.group(1).strip() if ph_url_m else f"https://www.producthunt.com/products/{name.lower().replace(' ', '-')}"

        off_url_m = re.search(r"\[公式サイト\]\((https://[^\)]+)\)", body)
        off_url = off_url_m.group(1).strip() if off_url_m else ""

        concept_m = re.search(r"\*\s*\*\*コンセプト\*\*:\s*\*\*(.+?)\*\*", body) or re.search(r"\*\s*\*\*コンセプト\*\*:\s*(.+)", body)
        concept = concept_m.group(1).strip() if concept_m else ""

        target_m = re.search(r"\*\s*\*\*想定ターゲット\*\*:\s*(.+)", body)
        target = target_m.group(1).strip() if target_m else ""

        adaptation_m = re.search(r"\*\s*\*\*事業化具体像\*\*:\s*(.+)", body)
        adaptation = adaptation_m.group(1).strip() if adaptation_m else ""

        needs_m = re.search(r"\*\s*\*\*💡\s*日本市場でのペイン・背景\*\*:\s*\n\s*\*\s*(.+)", body)
        needs = needs_m.group(1).strip() if needs_m else ""

        barriers_m = re.search(r"\*\s*\*\*参入障壁・配慮事項\*\*:\s*(.+)", body) or re.search(r"\*\s*\*\*⚖️\s*参入障壁[^\*]*\*\*:\s*(.+)", body)
        barriers = barriers_m.group(1).strip() if barriers_m else ""

        pricing_m = re.search(r"\*\s*\*\*💰\s*想定マネタイズ・価格帯\*\*:\s*(.+)", body) or re.search(r"\*\s*\*\*💰\s*想定収益モデル[^\*]*\*\*:\s*(.+)", body)
        pricing = pricing_m.group(1).strip() if pricing_m else ""

        recom_m = re.search(r"\*\s*\*\*🎯\s*推奨アクション\*\*:\s*(.+)", body) or re.search(r"\*\s*\*\*🏁\s*総合判定[^\*]*\*\*:\s*(.+)", body)
        recommendation = recom_m.group(1).strip() if recom_m else ""

        # adapt points
        adapt_points = []
        adapt_sec_m = re.search(r"日本版の必須機能・設計ポイント\*\*:\s*\n((?:\s*-\s*.+\n?)+)", body)
        if adapt_sec_m:
            for line in adapt_sec_m.group(1).splitlines():
                l = re.sub(r"^\s*-\s*", "", line).strip()
                if l: adapt_points.append(l)

        # competitors
        competitors = []
        comp_sec_m = re.search(r"日本の既存競合・代替ツール\*\*:\s*\n((?:\s*\*\s*.+\n?)+)", body)
        if comp_sec_m:
            for line in comp_sec_m.group(1).splitlines():
                cm = re.search(r"\*\*(.+?)\*\*:\s*(.+)", line)
                if cm:
                    competitors.append({"name": cm.group(1).strip(), "differentiation": cm.group(2).strip()})

        # SNS drafts
        post_draft_m = re.search(r"1通目[^\n]*\n```[^\n]*\n([\s\S]*?)```", body)
        post_draft = post_draft_m.group(1).strip() if post_draft_m else f"海外で話題の最新ツール「{name}」。{orig[:100]}..."

        reply_draft_m = re.search(r"2通目[^\n]*\n```[^\n]*\n([\s\S]*?)```", body)
        reply_draft = reply_draft_m.group(1).strip() if reply_draft_m else (
            f"🇯🇵 日本市場での着眼点：\n{concept}\n\n"
            f"👉 日本版MVPの具体的な機能要件・想定ARR試算は、プロフィール欄のnote週刊レポートにて徹底解剖しています📝"
        )

        p_id = name.lower().replace(" ", "-").replace(".", "").replace("/", "")

        items.append({
            "product_id": p_id,
            "name": name,
            "tagline": tagline,
            "description": orig,
            "ph_url": ph_url,
            "official_url": off_url,
            "category": "Tech / Web / AI",
            "first_seen_date": report_date,
            "analyzed_date": report_date,
            "rank": rank,
            "score": score,
            "one_line_summary": concept or f"{name}の日本展開モデル",
            "target_market": target or "法人 / スタートアップ",
            "pricing_model": pricing or "月額サブスクリプション",
            "jp_needs": needs,
            "jp_competitors": competitors,
            "jp_barriers": barriers,
            "jp_adaptation": adaptation,
            "recommendation": recommendation,
            "adapt_points": adapt_points,
            "original_summary_ja": orig,
            "sns_post_draft": post_draft,
            "sns_reply_draft": reply_draft,
        })

    return items

def main():
    db = Database()
    report_files = [
        Path("reports/2026-10-01_ProductHunt日次分析レポート.md"),
        Path("reports/2026-09-30_ProductHunt日次分析レポート.md"),
        Path("reports/2026-09-29_ProductHunt日次分析レポート.md"),
    ]

    total_added = 0
    for rf in report_files:
        if not rf.exists():
            print(f"[Skip] {rf} not found")
            continue
        items = parse_report_file(rf)
        print(f"Parsing {rf.name}: {len(items)} items")

        for it in items:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT count(*) FROM products WHERE id = ? OR name = ?", (it["product_id"], it["name"]))
                if cur.fetchone()[0] > 0:
                    continue

            # Save product
            db.save_product({
                "id": it["product_id"],
                "name": it["name"],
                "tagline": it["tagline"],
                "description": it["description"],
                "ph_url": it["ph_url"],
                "official_url": it["official_url"],
                "category": it["category"],
                "first_seen_date": it["first_seen_date"],
            })

            # Save evaluation
            eval_dict = {
                "rank": it["rank"],
                "score": it["score"],
                "one_line_summary": it["one_line_summary"],
                "target_market": it["target_market"],
                "pricing_model": it["pricing_model"],
                "jp_needs": it["jp_needs"],
                "jp_competitors": it["jp_competitors"],
                "jp_barriers": it["jp_barriers"],
                "jp_adaptation": it["jp_adaptation"],
                "recommendation": it["recommendation"],
                "adapt_points": it["adapt_points"],
                "original_summary_ja": it["original_summary_ja"],
                "sns_post_draft": it["sns_post_draft"],
                "sns_reply_draft": it["sns_reply_draft"],
            }
            db.save_evaluation(it["product_id"], eval_dict, it["analyzed_date"])
            total_added += 1

    print(f"\n==================================================")
    print(f"🎉 過去レポートからの取り込み完了！ 追加件数: {total_added} 件")
    all_evals = db.get_all_recent_evaluations(limit=200)
    print(f"DB内の合計評価件数: {len(all_evals)} 件")
    print(f"==================================================")

if __name__ == "__main__":
    main()
