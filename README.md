# 🚀 Product Hunt 日次収集＆日本市場ローカライズ事業判定システム

Product Huntから日々リリースされるプロダクトを自動収集し、LLM（Gemini）とWeb検索グラウンディングを用いて**「日本で置き換えたビジネス（タイムマシン経営・日本版ローカライズSaaS/サービス）が成立するか」**を多角的に分析・スコアリングして、Obsidian用Markdownレポートとブラウザ用HTMLダッシュボードを自動生成するシステムです。

---

## 🌟 主な特徴

1. **タイムマシン事業評価フレームワーク**:
   - 日本国内のペイン・ニーズ、既存競合（実在するSaaS/大企業ソリューション）、商習慣・法規制、日本版アレンジ案を徹底評価。
2. **Web検索連携（Google Search Grounding）**:
   - 国内の競合調査においてハルシネーションを防ぎ、実在する国内プレイヤーを特定して差別化ポイントを提示。
3. **公式LP（Landing Page）のテキスト自動抽出**:
   - 短いタグラインだけでなく、プロダクト公式サイトの主要コンテンツを自動取得して高解像度な分析を実現。
4. **SQLiteによる履歴管理・重複防止**:
   - 一度評価したプロダクトはローカルDB（`data/history.db`）に記録され、再実行時の二重分析（無駄なAPI消費）を防止。
5. **Obsidian連携（Dataview対応）**:
   - 生成される日次MarkdownレポートにはYAML Frontmatterが付与されており、Obsidianでのナレッジ管理や一覧抽出に最適。
6. **インタラクティブ HTML ダッシュボード**:
   - S/A/B/Cランク別フィルタ、インクリメンタル検索、詳細アコーディオン、ブックマーク機能付きのモダンUI。

---

## 🛠️ セットアップ手順

### 1. 環境構築 (初回のみ)
PowerShellを開き、本フォルダで仮想環境のセットアップと依存ライブラリのインストールを行います。

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

### 2. 環境変数の設定
`.env.example` をコピーして `.env` を作成し、必要なAPIキーを設定します。

```powershell
copy .env.example .env
```

`.env` の内容：
```env
# Gemini API Key (必須: AI分析および国内競合検索に使用)
GEMINI_API_KEY=your_actual_gemini_api_key

# Product Hunt API Token (任意: 未設定の場合は公式RSSフィードから自動取得)
PRODUCTHUNT_TOKEN=

# 分析モデル (デフォルト: gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash

# 日次取得件数上限 (デフォルト: 10)
DAILY_FETCH_LIMIT=10
```

---

## 💻 使い方

### 1. テスト実行（モックモード / APIキー不要）
APIキーを消費せず、パイプライン全行程（データ収集〜DB登録〜Markdownレポート〜HTMLダッシュボード生成）をテストできます。

```powershell
.\.venv\Scripts\python run_daily.py --mock
```

### 2. 本番日次実行
```powershell
.\.venv\Scripts\python run_daily.py
```

#### オプション一覧:
* `--mock`: テストデータを使用して即座にレポートを生成
* `--limit 3`: 分析するプロダクト数を指定（API消費を抑えて少件数で試す場合など）
* `--force`: 過去に分析済みのプロダクトもスキップせず強制再分析
* `--date 2026-09-21`: 日付を指定して実行

---

## 📁 成果物の格納場所

* **Markdownレポート**: `reports/YYYY-MM-DD_ProductHunt日次分析レポート.md`
  - Obsidian内でそのまま美しく閲覧・リンク可能。
* **HTMLダッシュボード**: `dashboard.html`
  - ブラウザでダブルクリックして開くと、全履歴の検索・フィルタリング・ブックマークが可能。
* **履歴データベース**: `data/history.db`
  - SQLite形式で過去の全分析結果を永続保管。

---

## ⏰ 自動実行（Windowsタスクスケジューラ）

Product Huntの更新サイクル（太平洋時間 23:59締め切り＝日本時間 16:00〜17:00頃）に合わせて、**毎日夕方17:30** または **毎朝8:00** にタスクスケジューラで以下を登録することで、完全自動運用が可能です。

* **プログラム/スクリプト**: `O:\03_Obsidian-Local\Obsidian-Local\13_ProductHunt分析\.venv\Scripts\python.exe`
* **引数の追加**: `run_daily.py`
* **開始 (作業フォルダー)**: `O:\03_Obsidian-Local\Obsidian-Local\13_ProductHunt分析`
