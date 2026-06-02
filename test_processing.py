"""
加工処理サービスのテスト
"""

from services import ProcessingService
from db import init_db, get_inventory_rows, get_process_lots
import json

# DB初期化
init_db()

# テスト用の投入在庫データを作成
test_selected_rows = [
    {
        "日付": "2026-06-01",
        "取引先": "TEST-CUSTOMER",
        "樹脂": "PP",
        "色": "N",
        "形状": "成形品",
        "荷姿": "フレコン",
        "在庫単位ID": "FC-TEST-001",
        "親ID": "",
        "重量kg": "600",
        "保管場所": "第1工場",
        "状態": "原料在庫",
        "備考": "テスト用"
    },
    {
        "日付": "2026-06-01",
        "取引先": "TEST-CUSTOMER",
        "樹脂": "PP",
        "色": "N",
        "形状": "成形品",
        "荷姿": "フレコン",
        "在庫単位ID": "FC-TEST-002",
        "親ID": "",
        "重量kg": "400",
        "保管場所": "第1工場",
        "状態": "原料在庫",
        "備考": "テスト用"
    },
]

# テスト用の加工後重量
test_output_weights = [500, 400]

print("=" * 60)
print("[TEST] ProcessingService Test")
print("=" * 60)

print("\nTest Conditions:")
print(f"  Input Items: {len(test_selected_rows)}")
print(f"  Input Total Weight: {sum(int(r['重量kg']) for r in test_selected_rows)} kg")
print(f"  Output Weights: {test_output_weights}")
print(f"  Output Total Weight: {sum(test_output_weights)} kg")
print(f"  Expected Loss: {sum(int(r['重量kg']) for r in test_selected_rows) - sum(test_output_weights)} kg")

print("\nExecuting processing...")

result = ProcessingService.execute_processing(
    selected_rows=test_selected_rows,
    process="粉砕",
    new_shape="粉砕",
    new_package="フレコン",
    new_location="第2工場",
    new_status="中間在庫",
    output_weights=test_output_weights,
    note="テスト実行",
)

print("\nResult:")
print(json.dumps(result, indent=2, ensure_ascii=False))

if result['success']:
    print(f"\nGenerated Lot ID: {result['lot_id']}")
    print(f"Generated Unit IDs: {', '.join(result['new_ids'])}")

    # DB から加工ロットを取得して確認
    process_lots = get_process_lots()
    if process_lots:
        latest_lot = process_lots[0]
        print("\nSaved Process Lot (in DB):")
        print(f"  Lot ID: {latest_lot.get('lot_id')}")
        print(f"  Process: {latest_lot.get('process')}")
        print(f"  Input IDs: {latest_lot.get('input_ids')}")
        print(f"  Output IDs: {latest_lot.get('output_ids')}")
        print(f"  Input Weight: {latest_lot.get('input_weight')} kg")
        print(f"  Output Weight: {latest_lot.get('output_weight')} kg")
        print(f"  Loss Weight: {latest_lot.get('loss_weight')} kg")

    print("\nTEST PASSED!")
else:
    print(f"\nERROR: {result['message']}")

print("\n" + "=" * 60)
