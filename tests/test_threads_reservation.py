import sys
import threading
import tempfile
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.storage.db import Database
from src.pipeline import DailyPipeline


def test_concurrent_same_product():
    """ケース1: 同一製品の同時予約 (2ワーカー、daily_limit=2) -> 予約IDは1つ、もう一方はNone"""
    print("\n[Test 1] 同一製品の同時予約テスト...")
    temp_file = Path(tempfile.gettempdir()) / f"test_same_prod_{threading.get_ident()}.db"
    if temp_file.exists():
        temp_file.unlink()

    db = Database(db_path=temp_file)
    barrier = threading.Barrier(2)
    results = []

    def worker():
        # BEGIN IMMEDIATE より前に同期
        barrier.wait()
        res = db.reserve_threads_post(
            product_id="prod-same",
            text="Test post",
            daily_limit=2,
        )
        results.append(res)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # 1つだけがint (record_id)、もう1つはNone
    successes = [r for r in results if r is not None]
    nones = [r for r in results if r is None]
    print(f"  -> 結果: 成功={len(successes)}件, 拒否={len(nones)}件")
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(nones) == 1, f"Expected 1 None, got {len(nones)}"

    try:
        temp_file.unlink()
    except Exception:
        pass
    print("  -> PASSED: 同一製品の同時重複予約が原子的に遮断されました。")


def test_concurrent_different_products_limit_1():
    """ケース2: 別製品の日次枠競合 (2ワーカー、別product_id、daily_limit=1) -> 予約IDは1つ、もう一方はNone、DBは1行"""
    print("\n[Test 2] 別製品の日次枠競合テスト (daily_limit=1)...")
    temp_file = Path(tempfile.gettempdir()) / f"test_diff_limit1_{threading.get_ident()}.db"
    if temp_file.exists():
        temp_file.unlink()

    db = Database(db_path=temp_file)
    barrier = threading.Barrier(2)
    results = []

    def worker(prod_id: str):
        barrier.wait()
        res = db.reserve_threads_post(
            product_id=prod_id,
            text=f"Test post for {prod_id}",
            daily_limit=1,
        )
        results.append((prod_id, res))

    t1 = threading.Thread(target=worker, args=("prod-A",))
    t2 = threading.Thread(target=worker, args=("prod-B",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r[1] is not None]
    nones = [r for r in results if r[1] is None]
    print(f"  -> 結果: 成功={len(successes)}件, 枠不足拒否={len(nones)}件")
    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(nones) == 1, f"Expected 1 None, got {len(nones)}"

    with db.get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM threads_posts").fetchone()[0]
        assert count == 1, f"Expected 1 DB row, got {count}"

    try:
        temp_file.unlink()
    except Exception:
        pass
    print("  -> PASSED: 日次枠（1件）の同時競合において、超過予約が原子的に遮断されました。")


def test_concurrent_different_products_limit_2():
    """ケース3: 上限以内の別製品 (2ワーカー、別product_id、daily_limit=2) -> 2件とも予約成功"""
    print("\n[Test 3] 上限以内の別製品予約テスト (daily_limit=2)...")
    temp_file = Path(tempfile.gettempdir()) / f"test_diff_limit2_{threading.get_ident()}.db"
    if temp_file.exists():
        temp_file.unlink()

    db = Database(db_path=temp_file)
    barrier = threading.Barrier(2)
    results = []

    def worker(prod_id: str):
        barrier.wait()
        res = db.reserve_threads_post(
            product_id=prod_id,
            text=f"Test post for {prod_id}",
            daily_limit=2,
        )
        results.append((prod_id, res))

    t1 = threading.Thread(target=worker, args=("prod-X",))
    t2 = threading.Thread(target=worker, args=("prod-Y",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    successes = [r for r in results if r[1] is not None]
    print(f"  -> 結果: 成功={len(successes)}件")
    assert len(successes) == 2, f"Expected 2 successes, got {len(successes)}"

    try:
        temp_file.unlink()
    except Exception:
        pass
    print("  -> PASSED: 上限枠内の正常な複数予約は妨げられずに受理されました。")


def test_pipeline_reservation_failure_suppresses_publisher():
    """ケース4: 予約失敗時にパイプラインが外部送信（Publisher）を一切呼ばないことの検証"""
    print("\n[Test 4] 予約失敗時のPublisher呼び出し完全抑止テスト...")
    temp_file = Path(tempfile.gettempdir()) / f"test_pipeline_suppress_{threading.get_ident()}.db"
    if temp_file.exists():
        temp_file.unlink()

    db = Database(db_path=temp_file)
    db.save_product({'id': 'prod-1', 'name': 'P1', 'tagline': 'T1', 'description': 'D1', 'ph_url': 'http://ph.com/1', 'first_seen_date': '2026-10-05'})
    db.save_evaluation('prod-1', {'rank': 'S', 'score': 90, 'one_line_summary': 'S1', 'sns_post_draft': 'Draft 1'}, '2026-10-05')

    pipeline = DailyPipeline(is_mock=False)
    pipeline.db = db

    # 既に予約・枠を消費した状態にする
    db.reserve_threads_post(product_id="prod-already", text="existing", daily_limit=1)

    class SpyPublisher:
        is_configured = True
        call_count = 0
        def publish(self, text, image_url=None):
            self.call_count += 1
            return "dummy_id"

    spy = SpyPublisher()
    pipeline.threads_publisher = spy

    evals = db.get_unposted_high_scoring_evaluations()
    pipeline._publish_top_product_to_threads(evals)

    print(f"  -> Publisher呼び出し回数: {spy.call_count}回")
    assert spy.call_count == 0, f"Expected 0 calls, got {spy.call_count}"

    try:
        temp_file.unlink()
    except Exception:
        pass
    print("  -> PASSED: 枠不足・予約失敗時にPublisherが一切呼び出されないことを確認しました。")


def test_pipeline_unknown_blocks_subsequent_runs():
    """ケース5: 結果不明（unknown）後の再実行で再送・他案件送信が完全に止まることの検証"""
    print("\n[Test 5] 結果不明（unknown）後の再実行抑止テスト...")
    temp_file = Path(tempfile.gettempdir()) / f"test_pipeline_unknown_{threading.get_ident()}.db"
    if temp_file.exists():
        temp_file.unlink()

    db = Database(db_path=temp_file)
    db.save_product({'id': 'prod-1', 'name': 'P1', 'tagline': 'T1', 'description': 'D1', 'ph_url': 'http://ph.com/1', 'first_seen_date': '2026-10-05'})
    db.save_evaluation('prod-1', {'rank': 'S', 'score': 90, 'one_line_summary': 'S1', 'sns_post_draft': 'Draft 1'}, '2026-10-05')
    db.save_product({'id': 'prod-2', 'name': 'P2', 'tagline': 'T2', 'description': 'D2', 'ph_url': 'http://ph.com/2', 'first_seen_date': '2026-10-05'})
    db.save_evaluation('prod-2', {'rank': 'S', 'score': 85, 'one_line_summary': 'S2', 'sns_post_draft': 'Draft 2'}, '2026-10-05')

    pipeline = DailyPipeline(is_mock=False)
    pipeline.db = db

    class TimeoutPublisher:
        is_configured = True
        call_count = 0
        def publish(self, text, image_url=None):
            self.call_count += 1
            return None  # タイムアウト等をシミュレート

    timeout_pub = TimeoutPublisher()
    pipeline.threads_publisher = timeout_pub

    evals = db.get_unposted_high_scoring_evaluations()
    # 1回目実行
    pipeline._publish_top_product_to_threads(evals)
    assert timeout_pub.call_count == 1

    # status=unknown がDBにあること
    with db.get_connection() as conn:
        row = conn.execute("SELECT status FROM threads_posts WHERE product_id = 'prod-1'").fetchone()
        assert row[0] == "unknown"

    # 2回目実行 (別の正常Publisherに差し替えても、枠消費済みで再送されない)
    class NormalPublisher:
        is_configured = True
        call_count = 0
        def publish(self, text, image_url=None):
            self.call_count += 1
            return "normal_id"

    normal_pub = NormalPublisher()
    pipeline.threads_publisher = normal_pub
    pipeline._publish_top_product_to_threads(evals)

    print(f"  -> 2回目実行での新規Publisher呼び出し回数: {normal_pub.call_count}回")
    assert normal_pub.call_count == 0, f"Expected 0 calls, got {normal_pub.call_count}"

    try:
        temp_file.unlink()
    except Exception:
        pass
    print("  -> PASSED: unknown状態により、手動確認前の自動再送・別案件送信が完全に抑止されました。")


if __name__ == "__main__":
    print("==================================================")
    print("🧪 Threads 排他制御・原子的予約 回帰テストスイート")
    print("==================================================")
    test_concurrent_same_product()
    test_concurrent_different_products_limit_1()
    test_concurrent_different_products_limit_2()
    test_pipeline_reservation_failure_suppresses_publisher()
    test_pipeline_unknown_blocks_subsequent_runs()
    print("\n==================================================")
    print("🎉 全5件の回帰テストに完全合格しました！")
    print("==================================================")
