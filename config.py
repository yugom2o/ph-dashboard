import os
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートディレクトリ
BASE_DIR = Path(__file__).resolve().parent

# .env ファイルの読み込み
load_dotenv(BASE_DIR / ".env")

# ディレクトリパス
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
TEMPLATES_DIR = BASE_DIR / "templates"
DOCS_DIR = BASE_DIR / "docs"
DASHBOARD_FILE = BASE_DIR / "dashboard.html"
DOCS_INDEX_FILE = DOCS_DIR / "index.html"
DB_PATH = DATA_DIR / "history.db"

# 必要なディレクトリの自動作成
for directory in [DATA_DIR, REPORTS_DIR, TEMPLATES_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# APIキー・設定値
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PRODUCTHUNT_TOKEN = os.getenv("PRODUCTHUNT_TOKEN", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
DAILY_FETCH_LIMIT = int(os.getenv("DAILY_FETCH_LIMIT", "10"))

# ダッシュボード保護＆GitHub Pages公開設定
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")

