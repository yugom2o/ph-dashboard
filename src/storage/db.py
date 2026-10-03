import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import DB_PATH


class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # プロダクト情報テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    tagline TEXT,
                    description TEXT,
                    ph_url TEXT UNIQUE NOT NULL,
                    official_url TEXT,
                    votes_count INTEGER DEFAULT 0,
                    category TEXT,
                    image_url TEXT,
                    first_seen_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # 日本市場評価テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    analyzed_date TEXT NOT NULL,
                    rank TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    one_line_summary TEXT,
                    target_market TEXT,
                    pricing_model TEXT,
                    jp_needs TEXT,
                    jp_competitors TEXT,
                    jp_barriers TEXT,
                    jp_adaptation TEXT,
                    recommendation TEXT,
                    raw_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
                """
            )
            # Threads投稿履歴テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS threads_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    text TEXT,
                    image_url TEXT,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
                """
            )
            # 既存テーブルへのカラム追加マイグレーション
            cursor.execute("PRAGMA table_info(products)")
            prod_cols = [c[1] for c in cursor.fetchall()]
            if "image_url" not in prod_cols:
                cursor.execute("ALTER TABLE products ADD COLUMN image_url TEXT")

            cursor.execute("PRAGMA table_info(threads_posts)")
            tp_cols = [c[1] for c in cursor.fetchall()]
            if "image_url" not in tp_cols:
                cursor.execute("ALTER TABLE threads_posts ADD COLUMN image_url TEXT")

            # インデックス
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_ph_url ON products(ph_url)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_analyzed_date ON evaluations(analyzed_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_rank ON evaluations(rank)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_threads_product_id ON threads_posts(product_id)")
            conn.commit()

    def is_already_analyzed(self, ph_url: str) -> bool:
        """指定されたProduct Hunt URLが既に評価済みか確認"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM evaluations e
                JOIN products p ON e.product_id = p.id
                WHERE p.ph_url = ?
                """,
                (ph_url,),
            )
            count = cursor.fetchone()[0]
            return count > 0

    def save_product(self, product_data: Dict[str, Any]) -> str:
        """プロダクト基本情報を保存（Upsert）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 既に同じURLのプロダクトが存在するか確認
            cursor.execute("SELECT id FROM products WHERE ph_url = ?", (product_data["ph_url"],))
            existing = cursor.fetchone()
            if existing:
                actual_id = existing[0]
                cursor.execute(
                    """
                    UPDATE products SET
                        name = ?,
                        tagline = ?,
                        description = ?,
                        official_url = coalesce(?, official_url),
                        votes_count = ?,
                        category = ?,
                        image_url = coalesce(?, image_url)
                    WHERE id = ?
                    """,
                    (
                        product_data["name"],
                        product_data.get("tagline", ""),
                        product_data.get("description", ""),
                        product_data.get("official_url"),
                        product_data.get("votes_count", 0),
                        product_data.get("category", ""),
                        product_data.get("image_url"),
                        actual_id,
                    ),
                )
                conn.commit()
                return actual_id

            cursor.execute(
                """
                INSERT INTO products (
                    id, name, tagline, description, ph_url, official_url,
                    votes_count, category, image_url, first_seen_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    tagline = excluded.tagline,
                    description = excluded.description,
                    official_url = coalesce(excluded.official_url, products.official_url),
                    votes_count = excluded.votes_count,
                    category = excluded.category,
                    image_url = coalesce(excluded.image_url, products.image_url)
                """,
                (
                    product_data["id"],
                    product_data["name"],
                    product_data.get("tagline", ""),
                    product_data.get("description", ""),
                    product_data["ph_url"],
                    product_data.get("official_url"),
                    product_data.get("votes_count", 0),
                    product_data.get("category", ""),
                    product_data.get("image_url"),
                    product_data.get("first_seen_date", datetime.now().strftime("%Y-%m-%d")),
                ),
            )
            conn.commit()
            return product_data["id"]

    def save_evaluation(self, product_id: str, eval_data: Dict[str, Any], analyzed_date: str) -> int:
        """評価結果を保存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            competitors_val = eval_data.get("jp_competitors", [])
            if isinstance(competitors_val, list):
                competitors_val = json.dumps([c.model_dump() if hasattr(c, "model_dump") else c for c in competitors_val], ensure_ascii=False)
            elif isinstance(competitors_val, dict):
                competitors_val = json.dumps(competitors_val, ensure_ascii=False)

            cursor.execute(
                """
                INSERT INTO evaluations (
                    product_id, analyzed_date, rank, score, one_line_summary, target_market,
                    pricing_model, jp_needs, jp_competitors, jp_barriers,
                    jp_adaptation, recommendation, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    analyzed_date,
                    eval_data.get("rank", "C"),
                    eval_data.get("score", 50),
                    eval_data.get("one_line_summary", ""),
                    eval_data.get("target_market", ""),
                    eval_data.get("pricing_model", ""),
                    eval_data.get("jp_needs", ""),
                    competitors_val,
                    eval_data.get("jp_barriers", ""),
                    eval_data.get("jp_adaptation", ""),
                    eval_data.get("recommendation", ""),
                    json.dumps(eval_data, ensure_ascii=False),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def _parse_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        if d.get("raw_json"):
            try:
                raw = json.loads(d["raw_json"])
                for k, v in raw.items():
                    if k not in d or not d[k] or k in ["adapt_points", "original_summary_ja"]:
                        d[k] = v
            except Exception:
                pass
        if d.get("jp_competitors") and isinstance(d["jp_competitors"], str):
            try:
                d["jp_competitors"] = json.loads(d["jp_competitors"])
            except Exception:
                pass
        return d

    def get_evaluations_by_date(self, target_date: str) -> List[Dict[str, Any]]:
        """指定日の評価結果一覧を取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.*, e.*
                FROM evaluations e
                JOIN products p ON e.product_id = p.id
                WHERE e.analyzed_date = ?
                ORDER BY e.score DESC
                """,
                (target_date,),
            )
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_all_recent_evaluations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """直近の評価結果一覧を取得（ダッシュボード用）"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.*, e.*
                FROM evaluations e
                JOIN products p ON e.product_id = p.id
                ORDER BY e.analyzed_date DESC, e.score DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [self._parse_row(row) for row in cursor.fetchall()]

    def get_evaluations_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """指定期間の評価結果一覧を取得"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.*, e.*
                FROM evaluations e
                JOIN products p ON e.product_id = p.id
                WHERE e.analyzed_date BETWEEN ? AND ?
                ORDER BY e.score DESC
                """,
                (start_date, end_date),
            )
            return [self._parse_row(row) for row in cursor.fetchall()]

    def is_already_posted_to_threads(self, product_id: str) -> bool:
        """指定されたプロダクトが既にThreadsに投稿済みか確認"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM threads_posts WHERE product_id = ?",
                (product_id,),
            )
            return cursor.fetchone()[0] > 0

    def record_threads_post(self, product_id: str, post_id: str, text: str, image_url: Optional[str] = None) -> int:
        """Threadsへの投稿実績を記録"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO threads_posts (product_id, post_id, text, image_url)
                VALUES (?, ?, ?, ?)
                """,
                (product_id, post_id, text, image_url),
            )
            conn.commit()
            return cursor.lastrowid
