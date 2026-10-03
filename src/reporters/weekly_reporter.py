import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import GEMINI_API_KEY, GEMINI_MODEL, REPORTS_DIR


class WeeklyReporter:
    def __init__(self, output_dir: Optional[Path] = None, model: str = GEMINI_MODEL):
        self.output_dir = output_dir or (REPORTS_DIR / "weekly")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.client = None
        if GEMINI_API_KEY:
            try:
                from google import genai
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception as e:
                print(f"[Warning] Failed to initialize Google GenAI client in WeeklyReporter: {e}")

    def generate_weekly_report(
        self,
        items: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        is_mock: bool = False,
    ) -> Path:
        """過去1週間のデータから週次トレンドレポート（note/ニュースレター用）を生成"""
        total = len(items)
        s_items = [it for it in items if it.get("rank") == "S"]
        a_items = [it for it in items if it.get("rank") == "A"]
        
        # 週番号の算出
        dt = datetime.strptime(end_date, "%Y-%m-%d")
        year, week_num, _ = dt.isocalendar()
        week_label = f"{year}-W{week_num:02d}"

        if is_mock or not self.client:
            analysis_text = self._generate_mock_weekly_analysis(items, s_items, a_items, start_date, end_date)
        else:
            analysis_text = self._call_gemini_weekly(items, s_items, a_items, start_date, end_date)

        md = []
        md.append("---")
        md.append("type: global-tech-weekly-report")
        md.append(f"week: {week_label}")
        md.append(f"period: {start_date} ~ {end_date}")
        md.append(f"total_analyzed: {total}")
        md.append(f"s_rank_count: {len(s_items)}")
        md.append(f"a_rank_count: {len(a_items)}")
        md.append("tags:")
        md.append("  - global-tech-radar")
        md.append("  - weekly-digest")
        md.append("  - timemachine-business")
        md.append("  - market-analysis")
        md.append("---")
        md.append("")
        md.append(analysis_text)

        out_file = self.output_dir / f"{week_label}_GlobalTech週報.md"
        out_file.write_text("\n".join(md), encoding="utf-8")
        return out_file

    def _call_gemini_weekly(
        self,
        items: List[Dict[str, Any]],
        s_items: List[Dict[str, Any]],
        a_items: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> str:
        """Geminiによる週次マクロトレンド・note原稿の生成"""
        # プロダクト情報の要約リストを作成
        summary_list = []
        for it in items[:30]:
            summary_list.append(
                f"- 【{it.get('rank')}ランク / {it.get('score')}点】{it.get('name')}: {it.get('tagline')}\n"
                f"  日本市場向け: {it.get('one_line_summary')} (ターゲット: {it.get('target_market')})"
            )
        products_context = "\n".join(summary_list)

        prompt = f"""あなたは海外テック・スタートアップの動向と日本市場（タイムマシン経営・ローカライズ事業）の専門リサーチャーです。
以下の【過去1週間に独自リサーチした海外注目テック・AIプロダクト一覧】を分析し、
noteや週刊ニュースレター（Substack等）にそのまま掲載できる、解像度の高い週刊トレンドレポート（Markdown）を作成してください。

### 【リサーチ対象期間】: {start_date} 〜 {end_date} (計{len(items)}プロダクト、Sランク: {len(s_items)}件、Aランク: {len(a_items)}件)

### 【収集プロダクト一覧（抜粋）】:
{products_context}

---

### 【構成と出力ルール】:
1. **メインタイトル**: 読者が読みたくなる魅力的で専門性の高いタイトル（例: 『【週刊】海外AIスタートアップ定点観測：〇〇領域の急成長と日本市場での勝機』）
2. **今週のマクロトレンド総括**: 今週ローンチされた海外プロダクトから見える共通の潮流・変化（3〜5行で鋭く考察）
3. **今週の注目カテゴリ＆キーワードTOP3**: どんな領域（例: 営業DX、自律型Agent、動画ローコード等）が熱かったか
4. **編集部厳選！日本上陸・ローカライズ期待のプロダクトTOP3**:
   - プロダクト名、概要、なぜ日本市場で刺さるのか、想定される日本版ビジネスモデルを詳しく解説
5. **日本市場でのタイムマシン事業チャンス（今週のインサイト）**: 日本の起業家・個人開発者・新規事業担当者が今すぐ仕掛けるべき論点
6. **X（Twitter）発信用ツリー投稿案**: この週報を要約した140字×3〜4連ツイート案

※注意: 情報源として「Product Hunt」などの外部媒体名は伏せ、「海外最新テック動向」「独自リサーチ」というスタンスで執筆してください。Markdown形式で出力してください。
"""
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                temperature=0.3,
            )
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return resp.text.strip()
        except Exception as e:
            print(f"[Warning] 週次Gemini分析の生成に失敗しました: {e}。モックにフォールバックします。")
            return self._generate_mock_weekly_analysis(items, s_items, a_items, start_date, end_date)

    def _generate_mock_weekly_analysis(
        self,
        items: List[Dict[str, Any]],
        s_items: List[Dict[str, Any]],
        a_items: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
    ) -> str:
        """モック用の高品質な週報テキスト"""
        featured = s_items + a_items
        if not featured:
            featured = items[:3]

        top_cards = []
        for it in featured[:3]:
            top_cards.append(
                f"### 🏆 【ランク {it.get('rank', 'A')} / {it.get('score', 80)}点】{it.get('name')}\n"
                f"- **海外公式キャッチコピー**: {it.get('tagline', '')}\n"
                f"- **ツール概要**: {it.get('original_summary_ja', it.get('description', ''))[:180]}...\n"
                f"- **🇯🇵 日本市場での勝機**: **{it.get('one_line_summary', '')}**\n"
                f"- **想定ターゲット**: {it.get('target_market', '中小企業・B2B')}\n"
                f"- **ビジネスモデル**: {it.get('pricing_model', '月額サブスクリプション')}\n"
            )
        cards_md = "\n".join(top_cards)

        return f"""# 🌐 【週刊】Global Tech Radar：海外最新AI・テック潮流と日本市場の勝機 ({start_date} ~ {end_date})

今週リサーチした **{len(items)}件** の海外最新プロダクトから、特に日本市場へのローカライズ（タイムマシン経営）成立性が高いモデルを総括分析します。

---

## 📈 今週のマクロトレンド総括
今週の海外スタートアップ市場では、**「単なるAIチャットボット」から「既存業務のタイムラインやワークフローに深く食い込むバーティカルAI」** へのシフトが明確になりました。
特に法人営業の事前リサーチ・スライド生成、長尺動画からの文脈抽出・ラフカット生成など、これまで専門スタッフが数時間〜数日かけていた属人作業を数分で終わらせるツールが大きな支持を集めています。

---

## 🔍 今週の注目潮流・キーワードTOP3
1. **営業特化型インサイト自動化**: 相手先WebサイトやIRを分析し、即座に商談用提案骨子を組み上げるSaaS
2. **クリエイター/広報向け自律編集AI**: インタビューなどの生動画から見どころをAIが判断し、粗編集を自動化
3. **ワークスペース統合エージェント**: Notion、Slack、CRMなどの既存ツールにアドオンして動くマイクロツール群

---

## 🚀 今週の厳選ピックアップ（日本市場での勝機大）

{cards_md}

---

## 💡 日本市場でのタイムマシン事業チャンス（今週のインサイト）
海外で支持されるモデルを日本市場に移植する際、共通して勝敗を分けるのは以下の3点です：
1. **「日本の業務エコシステム」への適応**: SalesforceやNotionだけでなく、freee、Sansan、PR TIMES、Slack/LINE WORKSとのシームレスな連携。
2. **商習慣に合わせたフォーマット出力**: 海外ではWeb上のダッシュボード完結が好まれますが、日本では「社内稟議に通しやすいPowerPoint(PPTX)形式」や「Excelエクスポート」の需要が根強く残っています。
3. **セキュリティと国内サポート**: 企業の独自データを取り扱うSaaSの場合、国内サーバー稼働や機密保持基準の明示が即決の鍵となります。

---

## 📱 X（Twitter）発信用ツリー投稿ドラフト案

```text
【今週の海外AIスタートアップ動向まとめ】
今週リサーチした{len(items)}ツールの中から、特に「日本でやったら絶対伸びる」有望モデルを3つ厳選しました。

1. 【Lead Sparker】企業URLから商談スライドを自動生成
2. 【Supacut】インタビュー生動画から要点を自動ラフカット
3. 【Jevtown】投稿前にAIペルソナ1万人が事前レビュー

深掘り考察をツリーで解説👇 (1/4)
```
"""
