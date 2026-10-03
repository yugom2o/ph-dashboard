# 🌐 Global Tech Radar 運用状況＆Threads自動化ステータス

> **最終更新日**: 2026-10-03  
> **ステータス**: 🟢 **完全自動稼働中 (クラウド実行・PCオフ対応)**

---

## 🎯 プロジェクト目的
海外でローンチ・急成長中の最新AIツールおよびTechプロダクトを毎朝自動収集し、**「日本市場でのタイムマシン事業（ローカライズビジネス）が成立するか」** をGeminiと検索連携で分析。  
特定プラットフォーム名（Product Hunt等）を伏せた独自リサーチブランド「**Global Tech Radar Japan**」として、メディア化およびSNS（Threads）発信を完全自動で行う。

---

## 🧵 Threads 自動投稿の運用状況

| 項目 | 設定内容 / ステータス |
| :--- | :--- |
| **公式アカウント** | **[@get_globaltechinfo](https://www.threads.net/@get_globaltechinfo)** |
| **実行環境** | **GitHub Actions (クラウドサーバー)** ※PCの電源オフでも確実に稼働 |
| **実行スケジュール** | **毎日 朝 06:35 (日本時間)** |
| **投稿対象** | 本日分析された中で最も有望なプロダクト（**SまたはAランクのTop 1件**） |
| **投稿内容** | フック ＋ 日本語解説 ＋ 日本市場での勝機 ＋ ハッシュタグ ＋ **製品ビジュアル画像添付** ＋ **純粋な公式サイト直通URL** |
| **添付画像** | **1024x512 高解像度製品ビジュアル / OGP画像**（Meta APIでの処理待機＆テキスト自動フォールバック機能付き） |
| **安全対策** | **SQLite二重投稿防止ガード**（過去に投稿したプロダクトは絶対に重複投稿しない） |
| **初回稼働実績** | **2026-10-03 成功**（プロダクト: Singularity / Post ID: 17995204095042230） |

---

## 🛠️ 今回完了した機能拡張・改善

1. **Threads画像付き自動投稿パイプライン (`src/publishers/threads_publisher.py`)**:
   - Meta公式Threads APIの `media_type="IMAGE"` に対応。
   - プロダクトのキービジュアル（1024x512 高画質バナー/OGP画像）を自動添付して投稿。
   - Metaサーバー側の画像処理ステータス（`FINISHED`）を最大30秒ポーリング待機。
   - **二重の安全ガード**: 万が一画像処理エラーやタイムアウトが発生しても、自動的にテキストのみの投稿へフォールバックして配信漏れを防止。
2. **高画質プロダクト画像の自動解決 (`src/enrichers/lp_scraper.py`)**:
   - Product Huntページおよびプロダクト公式サイトから `og:image` / `twitter:image` を高速抽出。
   - imgixパラメータ（`format=jpeg`）の自動正規化により、Meta画像クローラーとの互換性を確保。
   - 既存データベース内の全プロダクト（15件）も画像URLをバックフィル済み。
3. **Obsidianレポート＆Webダッシュボードのビジュアル化**:
   - Obsidianの日次Markdownレポートにプロダクトアイキャッチ画像をインライン表示。
   - ブラウザ用HTMLダッシュボード（[dashboard.html](file:///o:/03_Obsidian-Local/Obsidian-Local/13_ProductHunt%E5%88%86%E6%9E%90/dashboard.html)）の各カードにも洗練されたサムネイルバナーを追加。
4. **直接公式リンクの自動解決 (PHリダイレクト除去)**:
   - 収集元のアクセス追跡URL（`producthunt.com/r/...`）を自動追跡。
   - `?ref=producthunt` などのトラッキングパラメータを除去し、**純粋なプロダクト独自ドメインURL（例: `https://wattmateapp.com/`）** を抽出・掲載。
5. **クラウド自動実行体制（GitHub Actions）の確立**:
   - クラウド側のシークレットに `THREADS_ACCESS_TOKEN` を設定。
   - PCがスリープやシャットダウン状態でも、毎朝06:35にクラウド側で分析から画像付きThreads投稿まで完結。

---

## 📂 Obsidian内のファイル構成

* `00_システム設計・実装計画.md`: システム全体のアーキテクチャ・設計詳細
* `01_運用状況・Threads自動化ステータス.md`: 本ドキュメント（運用状況とThreads連携）
* `reports/YYYY-MM-DD_GlobalTech日次分析レポート.md`: 毎朝自動生成される日次レポート（アイキャッチ画像・SNSドラフト収録）
* `reports/weekly/YYYY-Wxx_GlobalTech週報.md`: 週末用の週刊トレンドまとめ
* `dashboard.html` / `docs/index.html`: ブラウザ閲覧用モダンダッシュボード（画像サムネイル対応・GitHub Pages連携）
* `data/history.db`: 分析履歴・画像URL・Threads投稿履歴を保管するSQLiteデータベース
* `test_threads.py`: Threads API接続テスト（`--post`, `--image` 対応）

---

## 🚀 次のネクストステップ（候補）

1. **Threadsのツリー投稿（親ポスト＋リプライの2段階投稿）**:
   - 1通目（フック＋核心概要＋画像）にぶら下げる形で、2通目（リプライ）に「日本市場でのタイムマシン事業チャンス＋公式サイト直通URL」を自動連投。
2. **note / ニュースレターへの週次展開**:
   - `run_weekly.py` で出力される週報を、週末にnoteへ自動フォーマットしてストック読者を獲得。
3. **X（Twitter）への同時展開**:
   - Threadsと同じ原稿・画像構成でX上にも自動同時ポスト。
