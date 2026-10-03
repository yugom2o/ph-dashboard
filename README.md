# 🌐 Global Tech Radar (海外最新テック＆日本市場適応レポート)

海外でローンチ・急成長中の最新AIツールおよびTechプロダクトを自動収集し、LLM（Gemini）とWeb検索グラウンディングを用いて**「日本で置き換えたビジネス（タイムマシン経営・日本版ローカライズSaaS/サービス）が成立するか」**を多角的に分析・スコアリングして、Obsidian用Markdownレポートとブラウザ用HTMLダッシュボード、SNS発信ドラフト、週刊まとめ原稿を自動生成するシステムです。

> [!NOTE]
> 本システムは外部メディア名への依存を排した独自リサーチブランド「**Global Tech Radar Japan**」として設計されており、集客メディアやSNS（X / note / ニュースレター）での情報発信・ブランディングにそのまま活用できます。

---

## 🌟 主な特徴

1. **タイムマシン事業評価フレームワーク**:
   - 日本国内のペイン・ニーズ、既存競合（実在するSaaS/大企業ソリューション）、商習慣・法規制、日本版アレンジ案を徹底評価。
2. **Threads への完全自動ポスト (公式Threads API)**:
   - 日次実行時、その日の最高スコア（S/Aランク）プロダクトをアカウント（`@get_globaltechinfo`）へ自動投稿。
   - SQLiteによる二重投稿防止機能付き（同じプロダクトを重複投稿しない安全設計）。
3. **SNS（X / Threads）発信ドラフトの自動生成**:
   - 各プロダクトについて、そのままコピペして発信できる魅力的な投稿文ドラフト（フック・要約・日本市場での勝機・ハッシュタグ）を自動生成。
4. **週次トレンド＆note/ニュースレター原稿生成 (`run_weekly.py`)**:
   - 過去1週間のデータをマクロ俯瞰し、「今週のトレンド総括」「注目カテゴリTOP3」「厳選ピックアップ」「note向け完成記事」を1クリックで生成。
5. **Discord / Slack Webhook通知**:
   - Sランク（即検討）案件検知時や日次完了時に、スマホへ即座にプッシュ通知。
5. **Web検索連携（Google Search Grounding）**:
   - 国内の競合調査においてハルシネーションを防ぎ、実在する国内プレイヤーを特定して差別化ポイントを提示。
6. **公式LP（Landing Page）のテキスト自動抽出**:
   - プロダクト公式サイトの主要コンテンツを自動取得して高解像度な分析を実現。
7. **インタラクティブ HTML ダッシュボード**:
   - S/A/B/Cランク別フィルタ、インクリメンタル検索、詳細アコーディオン、ブックマーク機能、ワンクリックSNSドラフトコピー機能付き。
8. **Obsidian連携（Dataview対応）**:
   - 生成される日次・週次MarkdownレポートにはYAML Frontmatterが付与されており、Obsidianでのナレッジ管理に最適。

---

## 🛠️ セットアップ手順

### 1. 環境構築 (初回のみ)
PowerShellを開き、本フォルダで仮想環境のセットアップと依存ライブラリのインストールを行います。

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env.example` をコピーして `.env` を作成し、必要なキーを設定します。

```powershell
copy .env.example .env
```

`.env` の内容：
```env
# Gemini API Key (必須: AI分析および国内競合検索に使用)
GEMINI_API_KEY=your_actual_gemini_api_key

# 収集用トークン (任意: 未設定の場合はRSS等から自動取得)
PRODUCTHUNT_TOKEN=

# 分析モデル (デフォルト: gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash

# 日次取得件数上限 (デフォルト: 10)
DAILY_FETCH_LIMIT=10

# 通知設定 (任意: Discord / Slack Webhook URL)
WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## 💻 使い方

### 1. 日次パイプラインの実行 (`run_daily.py`)

#### モックモード（テスト / APIキー不要）
```powershell
.\.venv\Scripts\python run_daily.py --mock
```

#### 本番日次実行
```powershell
.\.venv\Scripts\python run_daily.py
```

* オプション:
  * `--limit 5`: 分析件数を指定
  * `--force`: 過去分析済みをスキップせず強制再分析
  * `--date 2026-10-03`: 分析日を指定
  * `--threads`: Threads自動投稿を強制実行
  * `--no-threads`: Threads自動投稿をスキップ

---

### 2. 週次トレンド分析 & note原稿の生成 (`run_weekly.py`)

週末や週の初めに実行することで、1週間の蓄積データをマクロ分析し、noteやニュースレター向けの完成原稿を自動出力します。

#### 週報の生成
```powershell
.\.venv\Scripts\python run_weekly.py
```

* オプション:
  * `--mock`: モックモードで即座に週報Markdownを生成
  * `--days 7`: 集計対象の日数（デフォルト7日）
  * `--end-date 2026-09-25`: 集計終了日を指定

---

## 📁 成果物の格納場所

* **日次Markdownレポート**: `reports/YYYY-MM-DD_GlobalTech日次分析レポート.md`
  - 各プロダクトの詳細分析および「📱 本日のSNS発信ドラフト」を収録。
* **週次Markdownレポート**: `reports/weekly/YYYY-Wxx_GlobalTech週報.md`
  - マクロトレンド、注目カテゴリ、厳選TOP3、note用記事全文、Xスレッド案を収録。
* **HTMLダッシュボード**: `dashboard.html` (`docs/index.html`)
  - ブラウザで閲覧・検索・ブックマーク・SNSドラフトコピーが可能。
* **履歴データベース**: `data/history.db`
  - SQLite形式で過去の全分析結果を永続保管。

---

## ⏰ 自動実行（Windowsタスクスケジューラ）

日次更新に合わせて **毎夕17:30** または **毎朝8:00** にタスクスケジューラで以下を登録することで、完全自動運用が可能です。

* **プログラム/スクリプト**: `O:\03_Obsidian-Local\Obsidian-Local\13_ProductHunt分析\.venv\Scripts\python.exe`
* **引数の追加**: `run_daily.py`
* **開始 (作業フォルダー)**: `O:\03_Obsidian-Local\Obsidian-Local\13_ProductHunt分析`

※ 週次レポート（`run_weekly.py`）を毎週月曜朝または日曜夜に自動実行するスケジュールも同様に追加可能です。
