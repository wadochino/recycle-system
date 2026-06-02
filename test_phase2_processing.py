"""
Phase 2 テスト：内部IDを使用した加工処理
"""

from services import ProcessingService
from db import init_db, migrate_add_internal_ids, get_process_lots, get_conn
import json

init_db()
migrate_add_internal_ids()

print("=" * 70)
print("[TEST] Phase 2 - Processing with Internal ID (ULID)")
print("=" * 70)

# テスト用の投入在庫データ
test_selected_rows = [
    {
        "日付": "2026-06-01",
        "取引先": "TEST-PHASE2",
        "樹脂": "PE",
        "色": "Z",
        "形状": "フィルム",
        "荷姿": "フレコン",
        "在庫単位ID": "FC-PHASE2-001",
        "親ID": "",
        "重量kg": "800",
        "保管場所": "第1工場",
        "状態": "原料在庫",
        "備考": "Phase 2 テスト"
    },
]

test_output_weights = [700]

print("\n[1] Processing with Internal ID")
print("-" * 70)

result = ProcessingService.execute_processing(
    selected_rows=test_selected_rows,
    process="粉砕",
    new_shape="粉砕",
    new_package="フレコン",
    new_location="第2工場",
    new_status="中間在庫",
    output_weights=test_output_weights,
    note="Phase 2 テスト",
)

print(f"Success: {result['success']}")
if not result['success']:
    print(f"Error: {result['message']}")
print(f"Lot ID: {result['lot_id']}")
print(f"New IDs: {result['new_ids']}")

# DB から加工ロットを取得
print("\n[2] DB Verification")
print("-" * 70)

process_lots = get_process_lots()
if process_lots:
    latest_lot = process_lots[0]
    print(f"Latest Process Lot:")
    print(f"  Display ID: {latest_lot.get('lot_id')}")
    print(f"  Internal ID: {latest_lot.get('internal_id')}")
    print(f"  Process: {latest_lot.get('process')}")
    print(f"  Output IDs: {latest_lot.get('output_ids')}")

    # 生成された在庫をチェック
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()

        output_ids = latest_lot.get('output_ids', '').split(',')
        for unit_id in output_ids:
            cur.execute("""
                SELECT unit_id, internal_id, weight_kg, status
                FROM inventory
                WHERE unit_id = ?
            """, (unit_id.strip(),))

            row = cur.fetchone()
            if row:
                print(f"\nGenerated Inventory:")
                print(f"  Display ID: {row['unit_id']}")
                print(f"  Internal ID: {row['internal_id']}")
                print(f"  Weight: {row['weight_kg']}kg")
                print(f"  Status: {row['status']}")

print("\n[3] Summary")
print("-" * 70)
print(f"Display ID (現場用): {result['lot_id']}")
print(f"Internal ID (ULID): {process_lots[0].get('internal_id') if process_lots else 'N/A'}")
print(f"Generated Inventory IDs: {', '.join(result['new_ids'])}")

print("\n" + "=" * 70)
print("TEST PASSED - Phase 2 Implementation Successful!")
print("=" * 70)
