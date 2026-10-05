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

        # note / ニュースレター コピペ用プレーンファイル
        note_dir = self.output_dir / "note"
        note_dir.mkdir(parents=True, exist_ok=True)
        note_file = note_dir / f"{week_label}_note投稿原稿.md"
        note_file.write_text(analysis_text, encoding="utf-8")

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
            img_info = f" (画像URL: {it.get('image_url')})" if it.get('image_url') else ""
            url_info = f" (公式URL: {it.get('official_url')})" if it.get('official_url') else ""
            summary_list.append(
                f"- 【{it.get('rank')}ランク / {it.get('score')}点】{it.get('name')}: {it.get('tagline')}{url_info}{img_info}\n"
                f"  日本市場向け: {it.get('one_line_summary')} (ターゲット: {it.get('target_market')})\n"
                f"  機能概要: {it.get('original_summary_ja', it.get('description', ''))[:150]}"
            )
        # スコア順にソート（降順）
        sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
        top_candidates = [it for it in sorted_items if it.get("score", 0) >= 70]
        if len(top_candidates) < 5:
            top_candidates = sorted_items[:5]
        
        # 無料枠＝注目候補中の下位3件（Aランク下位3つ）、有料枠＝それより上位（Sランク・Aランク上位）
        free_items = top_candidates[-3:] if len(top_candidates) >= 3 else top_candidates
        paid_items = top_candidates[:-3] if len(top_candidates) >= 3 else []

        def format_product_info(item_list):
            lines = []
            for it in item_list:
                img_info = f" (画像URL: {it.get('image_url')})" if it.get('image_url') else ""
                url_info = f" (公式URL: {it.get('official_url')})" if it.get('official_url') else ""
                lines.append(
                    f"- 【{it.get('rank')}ランク / {it.get('score')}点】{it.get('name')}: {it.get('tagline')}{url_info}{img_info}\n"
                    f"  概要: {it.get('original_summary_ja', it.get('description', ''))[:150]}\n"
                    f"  タイムマシン事業化案: {it.get('one_line_summary')}\n"
                    f"  想定ターゲット: {it.get('target_market')}\n"
                    f"  ビジネスモデル: {it.get('pricing_model')}"
                )
            return "\n".join(lines)

        paid_context = format_product_info(paid_items)
        free_context = format_product_info(free_items)

        # 一覧リストの作成（有料公開分はプロダクト名をマスクし、無料公開分はすべて明記）
        list_lines = []
        for idx, it in enumerate(sorted_items, 1):
            if it in free_items:
                # 無料公開ツール
                list_lines.append(f"{idx}. **{it.get('name')}** 【ランク {it.get('rank')} / {it.get('score')}点】\n   - {it.get('one_line_summary', it.get('tagline', ''))}")
            elif it in paid_items:
                # 有料公開ツール（プロダクト名をマスク）
                list_lines.append(f"{idx}. **【🔒 メンバー限定公開】** 【ランク {it.get('rank')} / {it.get('score')}点】\n   - {it.get('one_line_summary', it.get('tagline', ''))}")
            else:
                # B/Cランクのその他ツール
                list_lines.append(f"{idx}. **{it.get('name')}** 【ランク {it.get('rank')} / {it.get('score')}点】\n   - {it.get('one_line_summary', it.get('tagline', ''))}")
        product_list_text = "\n".join(list_lines)

        prompt = f"""あなたは海外テック・スタートアップの動向と日本市場（タイムマシン経営・ローカライズ事業）の専門リサーチャーです。
以下の【独自リサーチした海外注目テックプロダクト】を分析し、
note（メンバーシップ / 有料記事）にそのまま掲載できる、**無料公開エリア**と**有料会員限定エリア**が明確に分かれた完成原稿（Markdown）を作成してください。

### 【リサーチ対象期間】: {start_date} 〜 {end_date} (計{len(items)}プロダクト)

---

### 【記事全体の構成ルール】:

#### ■ 1. 無料公開エリア（誰でも読めるパート）
1. **メディア紹介ヘッダー**: 
   > 🌐 **Global Tech Radar Japan**：海外でローンチ・急成長中の最新AIツールおよびTechプロダクトを毎朝自動収集し、「日本市場でのタイムマシン事業（ローカライズビジネス）が成立するか」を分析する独自メディアです。毎朝の速報は [Threads (@get_globaltechinfo)](https://www.threads.net/@get_globaltechinfo) にて配信中。
2. **メインタイトル**: 読者が読みたくなる魅力的で専門性の高いタイトル（例: 『【週刊】海外AIスタートアップ定点観測：〇〇領域の急成長と日本市場での勝機』）
3. **今週のマクロトレンド総括**: 今週の海外プロダクトから見える共通潮流・変化（3〜5行で鋭く考察）
4. **今週の注目カテゴリ＆キーワードTOP3**: どんな領域が熱かったか
5. **当メディア独自の評価ランク定義**:
   読者がスコアの価値を理解できるよう、以下の基準を明記してください：
   - 🏆 **Sランク (90点〜)**: 日本市場で今すぐ参入すべき最有望モデル。海外でのトラクションが高く、国内競合が不在。
   - 🥇 **Aランク (70〜89点)**: 日本市場での勝機が大きい注目モデル。業務プロセスや商習慣のローカライズで急成長が狙える。
   - 🥈 **Bランク (50〜69点)**: 検証の余地あり。国内競合が強固であるか、特定ニッチ特化が必要。
   - 🥉 **Cランク (〜49点)**: 国内展開の難易度高、または機能が単機能にとどまるもの。

   ※必ずランク定義の直下に以下の免責事項ブロック（引用文）を記載してください：
   > ⚠️ **【免責事項・ご利用にあたって】**  
   > 当メディアで提供する分析スコア、ランク判定（S/A/B/C）、およびタイムマシン事業化プラン・試算数値は、海外公開データやAIによる定点観測に基づく**あくまで参考情報・アイデアの種**です。特定の事業の成功、収益性、法規制への適合を保証するものではありません。実際の起業・開発・投資等の意思決定は、ご自身の判断と責任において行っていただきますようお願いいたします。
6. **今週リサーチした全{len(items)}プロダクト一覧**:
   ※有料公開分のプロダクト名は「【🔒 メンバー限定公開】」とマスクされています。以下のリストをそのまま綺麗に掲載してください：
{product_list_text}
7. **🆓 【無料公開枠】今週の注目ピックアップ（Aランク下位3選）**:
   ※「今週高評価を獲得したAランクツールの中から、下位の3ツールとそのタイムマシン事業化プランを無料公開します」と明記してください。
   以下の3件について詳細を記載してください：
{free_context}
   ※重要: **各ツールの「日本市場でのタイムマシン事業化プラン」は必ず具体的に記載してください！**
   - 見出し（H3）: 🏆 【ランク A / YY点】プロダクト名
   - 画像（画像URLがあれば Markdown形式 `![プロダクト名](画像URL)` で掲載）
   - 公式サイトリンク: `🔗 公式サイト: [URL](URL)`
   - ツール概要
   - 🇯🇵 **日本市場でのタイムマシン事業化プラン**: （具体的な事業アイデア・想定ターゲット・ビジネスモデル）

---

#### ■ 2. 有料ライン（Paywallの境界線）
以下のような、noteの有料ライン設定（またはメンバーシップ限定公開設定）の位置がひと目でわかり、読者の購読意欲を最大化する境界線ブロックを挿入してください：
```markdown
---

## 🔒 ここから先は「Global Tech Lab」有料メンバー限定エリア

> 💡 **note編集部からのお知らせ**:
> このラインより下は、**月額メンバーシップ会員（または記事単体購入者）限定**のコンテンツです。
> （※noteで投稿する際は、noteエディタの「有料エリア指定」バーをこの位置に配置してください）

### 🎁 【有料メンバー限定の特典】
1. 🏆 **今週の最上位「Sランク」およびAランク上位ツールの実名公開＆詳細解剖**
2. 💰 **日本版MVPの具体的機能要件・想定ARR試算・推奨プライシング**
3. 🔑 **会員限定「暗号化Webダッシュボード（全件DB）」の閲覧合言葉（パスワード）**
4. 💼 **法人向け海外テック調査・新規事業リサーチの優先相談権**

---
```

---

#### ■ 3. 有料会員限定エリア
8. **🔒 【メンバー限定】最上位・Sランク＆Aランク上位プロダクト徹底解剖**:
   以下の有料枠プロダクト（Sランク・Aランク上位）について、実名を公開し深い解像度で詳細を記載してください：
{paid_context}
   ※重要: **有料枠の各プロダクトについても「日本市場でのタイムマシン事業化プラン（詳細なMVP仕様・想定ARR・推奨プライシング）」をすべて明記してください！**
9. **🔑 【会員限定特典】Webダッシュボード合言葉のご案内**:
   「当メディア公式の暗号化Webダッシュボード（過去の全分析データ・検索・しおり機能付き）へアクセスするための最新合言葉は、メンバーシップ加入特典ページにてご案内しています。」と案内してください。
10. **💡 日本市場でのタイムマシン事業チャンス（今週の戦略インサイト）**: 日本の起業家・開発者が仕掛けるべき論点
11. **💬 メンバー限定ディスカッション**: 「今週紹介したツールの中で、日本のどの業界向けなら最も早くマネタイズできると思いますか？コメント欄でぜひご意見をお聞かせください。」
12. **💼 【法人向け】海外競合リサーチ・新規事業壁打ちのご相談窓口**:
    以下の問い合わせ案内ブロックを必ず掲載してください：
    ```markdown
    ---
    ### 🤝 企業・新規事業開発担当者様へ
    当メディアでは、特定業界（HR、SaaS、マーケティング、金融等）に特化した**海外スタートアップ定点観測**や、
    **特定海外プロダクトの日本参入可能性・競合リサーチ**の個別受託・壁打ちも承っております。
    自社事業へのタイムマシン展開やPoC開発をご検討の企業様は、下記フォームよりお気軽にご相談ください。
    👉 **[海外テック・競合リサーチ お問い合わせフォーム（Googleフォーム）](https://forms.gle/FkJiAb57xF5kfQec9)**
    ```
13. **編集後記 & リンク**: Threadsの案内、Webダッシュボード案内

※注意: 「Product Hunt」等の外部媒体名は伏せ、「独自リサーチ」として執筆してください。Markdown形式で出力してください。
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
        """モック用の高品質な週報テキスト（下位3つ無料、上位有料、タイムマシン事業化プラン全記載）"""
        sorted_items = sorted(items, key=lambda x: x.get("score", 0), reverse=True)
        top_candidates = [it for it in sorted_items if it.get("score", 0) >= 70]
        if len(top_candidates) < 5:
            top_candidates = sorted_items[:5]

        # 無料枠＝ピックアップ中の下位3件、有料枠＝それより上位
        free_items = top_candidates[-3:] if len(top_candidates) >= 3 else top_candidates
        paid_items = top_candidates[:-3] if len(top_candidates) >= 3 else []

        def build_cards(target_list, is_premium=False):
            cards = []
            for it in target_list:
                img_md = f"![{it.get('name')} 製品ビジュアル]({it.get('image_url')})\n\n" if it.get("image_url") else ""
                off_md = f"- **🔗 公式サイト**: [{it.get('official_url')}]({it.get('official_url')})\n" if it.get("official_url") else ""
                badge = "🔒 【メンバー限定】" if is_premium else "🆓 【無料公開】"
                cards.append(
                    f"### {badge} 🏆 【ランク {it.get('rank', 'A')} / {it.get('score', 80)}点】{it.get('name')}\n"
                    f"{img_md}"
                    f"{off_md}"
                    f"- **海外公式キャッチコピー**: {it.get('tagline', '')}\n"
                    f"- **ツール概要**: {it.get('original_summary_ja', it.get('description', ''))[:200]}...\n"
                    f"- **🇯🇵 日本市場でのタイムマシン事業化プラン**: **{it.get('one_line_summary', '')}**\n"
                    f"- **想定ターゲット顧客**: {it.get('target_market', '中小企業・B2B')}\n"
                    f"- **推奨マネタイズモデル**: {it.get('pricing_model', '月額サブスクリプション')}\n"
                )
            return "\n".join(cards)

        free_cards_md = build_cards(free_items, is_premium=False)
        paid_cards_md = build_cards(paid_items, is_premium=True)

        return f"""> 🌐 **Global Tech Radar Japan**：海外でローンチ・急成長中の最新AIツールおよびTechプロダクトを毎朝自動収集し、**「日本市場でのタイムマシン事業（ローカライズビジネス）が成立するか」** を分析する独自リサーチメディアです。  
> 毎朝の速報・高画質ビジュアル付きポストは **[Threads (@get_globaltechinfo)](https://www.threads.net/@get_globaltechinfo)** にて完全自動配信中。

# 🌐 【週刊】Global Tech Radar：海外最新AI・テック潮流と日本市場の勝機 ({start_date} ~ {end_date})

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

## 🆓 【無料公開エリア】今週の注目ピックアップ3選
今週ピックアップした有望株のうち、まずは**下位3ツールとその「日本市場でのタイムマシン事業化プラン」**を完全無料公開します！

{free_cards_md}

---

## 🔒 ここから先は「Global Tech Lab」有料メンバー限定エリア

> 💡 **note編集部からのお知らせ**:
> このラインより下は、**月額メンバーシップ会員（または記事単体購入者）限定**のコンテンツです。
> （※noteで投稿する際は、noteエディタの「有料エリア指定」バーをこの位置に配置してください）

### 🎁 【有料メンバー限定の特典】
1. 🏆 **今週の最上位「Sランク」およびAランク上位ツールの実名公開＆詳細解剖**
2. 💰 **日本版MVPの具体的機能要件・想定ARR試算・推奨プライシング**
3. 🔑 **会員限定「暗号化Webダッシュボード（全件DB）」の閲覧合言葉（パスワード）**
4. 💼 **法人向け海外テック調査・新規事業リサーチの優先相談権**

---

## 🔒 【メンバー限定】最上位・Sランク＆上位プロダクト徹底解剖

{paid_cards_md}

---

## 🔑 【会員限定特典】Webダッシュボード合言葉のご案内
当メディア公式の**暗号化Webダッシュボード**（過去すべての分析データベース、検索、しおり機能）へアクセスするための最新の合言葉は、メンバーシップ加入特典ページにてご案内しています。

👉 **[Webダッシュボードを開く](https://yugom2o.github.io/ph-dashboard/)**

---

## 💡 日本市場でのタイムマシン事業チャンス（今週のインサイト）
海外で支持されるモデルを日本市場に移植する際、共通して勝敗を分けるのは以下の3点です：
1. **「日本の業務エコシステム」への適応**: SalesforceやNotionだけでなく、freee、Sansan、PR TIMES、Slack/LINE WORKSとのシームレスな連携。
2. **商習慣に合わせたフォーマット出力**: 海外ではWeb上のダッシュボード完結が好まれますが、日本では「社内稟議に通しやすいPowerPoint(PPTX)形式」や「Excelエクスポート」の需要が根強く残っています。
3. **セキュリティと国内サポート**: 企業の独自データを取り扱うSaaSの場合、国内サーバー稼働や機密保持基準の明示が即決の鍵となります。

---

## 💬 メンバー限定ディスカッション（意見募集中！）
今週取り上げたプロダクトの中で、**「日本のこの業界向けに特化したら勝てるのでは？」「自分ならこういうアレンジで作る」** というアイデアやご意見があれば、ぜひコメント欄で教えてください！メンバーの皆さんの知見をお待ちしています。

---

### 🤝 企業・新規事業開発担当者様へ
当メディアでは、特定業界（HR、SaaS、マーケティング、金融等）に特化した**海外スタートアップ定点観測**や、**特定海外プロダクトの日本参入可能性・競合リサーチ**の個別受託・壁打ちも承っております。  
自社事業へのタイムマシン展開やPoC開発をご検討の企業様は、下記フォームよりお気軽にご相談ください。  
👉 **[海外テック・競合リサーチ お問い合わせフォーム（Googleフォーム）](https://forms.gle/FkJiAb57xF5kfQec9)**

---

## 📣 編集後記 & リンク
* ⚡ **毎朝の速報（Threads）**: [@get_globaltechinfo](https://www.threads.net/@get_globaltechinfo) をフォローして最新AIツールを毎朝チェック
* 📊 **Webダッシュボード**: [直近の分析データベースを閲覧する](https://yugom2o.github.io/ph-dashboard/)
"""
