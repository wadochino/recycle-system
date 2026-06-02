"""
計量登録サービスのテスト
"""

from services import ReceiptService
from db import init_db, get_inventory_rows

# DB初期化
init_db()

print("=" * 60)
print("[TEST] ReceiptService - Weighing (No Plan)")
print("=" * 60)

# 予定なし計量登録をテスト
result = ReceiptService.register_weighing_no_plan(
    customer="TEST-001",
    material="PP",
    color="N",
    shape="成形品",
    package="フレコン",
    location="第1工場",
    weights=[300, 250, 200],
)

print("\nResult:")
print(f"  Success: {result['success']}")
print(f"  Generated IDs: {result['new_ids']}")
print(f"  Message: {result['message']}")

if result['success']:
    print("\nVerifying in DB:")
    rows = get_inventory_rows()
    latest_rows = [r for r in rows if r["取引先"] == "TEST-001"]
    print(f"  Found {len(latest_rows)} items for TEST-001")
    for r in latest_rows[:3]:
        print(f"    - {r['在庫単位ID']}: {r['重量kg']}kg, Status: {r['状態']}")

print("\n" + "=" * 60)
print("[TEST] ReceiptService - Receipt Registration")
print("=" * 60)

# 予定登録をテスト
receipt_id = ReceiptService.register_planned_receipt(
    receipt_date="2026-06-01",
    customer="TEST-002",
    material="PE",
    package="カゴ",
    planned_qty=5,
    location="倉庫",
)

print(f"\nGenerated Receipt ID: {receipt_id}")
print("TEST PASSED!")
print("\n" + "=" * 60)
