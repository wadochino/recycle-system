"""
出荷処理サービスのテスト
"""

from services import ShippingService
from db import init_db, insert_inventory_row, get_inventory_rows

# DB初期化
init_db()

print("=" * 60)
print("[TEST] ShippingService - Register Shipping")
print("=" * 60)

# テスト用の出荷対象在庫を作成
print("\nCreating test inventory...")
test_inventory = {
    "日付": "2026-06-01",
    "取引先": "SHIP-TEST",
    "樹脂": "PP",
    "色": "N",
    "形状": "ペレット",
    "荷姿": "フレコン",
    "在庫単位ID": "FC-SHIP-TEST-001",
    "親ID": "",
    "重量kg": "500",
    "保管場所": "出荷ヤード",
    "状態": "製品在庫",
    "備考": "出荷テスト用"
}

insert_inventory_row(test_inventory)
print(f"Created test inventory: FC-SHIP-TEST-001")

# 出荷処理をテスト
print("\nExecuting shipping...")
result = ShippingService.register_shipping(
    selected_ids=["FC-SHIP-TEST-001"],
    ship_date="2026-06-01",
    destination="CUSTOMER-A",
    note="テスト出荷",
)

print("\nResult:")
print(f"  Success: {result['success']}")
print(f"  Count: {result['count']} items")
print(f"  Message: {result['message']}")

if result['success']:
    print("\nVerifying in DB:")
    rows = get_inventory_rows()
    shipped = [r for r in rows if r["在庫単位ID"] == "FC-SHIP-TEST-001"]
    if shipped:
        r = shipped[0]
        print(f"  Status: {r['状態']}")
        print(f"  Note: {r['備考']}")

print("\nTEST PASSED!")
print("=" * 60)
