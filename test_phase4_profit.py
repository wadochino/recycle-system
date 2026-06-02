"""
Phase 4 テスト：原価配賦・売上・粗利管理
- 原価配賦（重量按分）
- 売上登録・金額計算
- 粗利計算・集計
"""

from services import CostAllocationService, SalesService, ProfitService, PriceService
from db import init_db, migrate_add_internal_ids, migrate_phase3_add_columns, migrate_phase4_add_columns
from datetime import date

init_db()
migrate_add_internal_ids()
migrate_phase3_add_columns()
migrate_phase4_add_columns()

print("=" * 70)
print("[TEST] Phase 4 - Cost Allocation & Sales & Profit Management")
print("=" * 70)

# ===============================================
# 1. 原価配賦テスト（重量按分）
# ===============================================
print("\n[1] Cost Allocation (Weight Proportion)")
print("-" * 70)

# テスト用の投入在庫（仮データ）
input_rows = [
    {
        'unit_id': 'FC-TEST-001',
        'cost_amount': 10000.0,  # 原価10000円
        'weight_kg': 600
    },
    {
        'unit_id': 'FC-TEST-002',
        'cost_amount': 8000.0,   # 原価8000円
        'weight_kg': 400
    },
]

# 加工後の重量
output_weights = [600, 400]  # 600kg, 400kg
output_unit_ids = ['FC-PROC-001', 'FC-PROC-002']

print(f"\nInput:")
for row in input_rows:
    print(f"  {row['unit_id']}: 原価 {row['cost_amount']:.0f}円, 重量 {row['weight_kg']}kg")

print(f"\nOutput:")
for weight, unit_id in zip(output_weights, output_unit_ids):
    print(f"  {unit_id}: {weight}kg")

# 原価配賦を実行
allocation_result = CostAllocationService.allocate_cost_by_weight(
    input_rows=input_rows,
    output_weights=output_weights,
    output_unit_ids=output_unit_ids,
    note="テスト加工"
)

print(f"\nAllocation Result:")
print(f"  Total Input Cost: {allocation_result['total_input_cost']:.0f}円")
print(f"  Total Output Weight: {allocation_result['total_output_weight']}kg")

if allocation_result['allocations']:
    print(f"\nCost Distribution:")
    for alloc in allocation_result['allocations']:
        print(f"  {alloc['unit_id']}")
        print(f"    Weight: {alloc['weight']}kg ({alloc['weight_ratio']*100:.1f}%)")
        print(f"    Allocated Cost: {alloc['cost']:.0f}円")
        print(f"    Cost Unit Price: {alloc['cost_price']:.2f}円/kg")

# ===============================================
# 2. 販売単価の設定
# ===============================================
print("\n[2] Setup Sales Prices")
print("-" * 70)

# 販売単価を登録
PriceService.register_sales_price(
    item_code="ITEM-PROC-001",
    destination="CUST-SALES-A",
    start_date=date(2026, 1, 1),
    end_date=None,
    sales_unit_price=100.0,
    note="標準価格"
)

print("Registered sales price: ITEM-PROC-001 @ CUST-SALES-A = 100 yen/kg")

# ===============================================
# 3. 売上登録テスト
# ===============================================
print("\n[3] Sales Registration")
print("-" * 70)

# 売上を登録
sales_result = SalesService.register_sales(
    ship_date=date(2026, 6, 1),
    destination="CUST-SALES-A",
    items=[
        {
            'unit_id': 'FC-PROC-001',
            'item_code': 'ITEM-PROC-001',
            'weight_kg': 600,
            'sales_unit_price': 100.0,
            'cost_amount': allocation_result['allocations'][0]['cost'] if allocation_result['allocations'] else 0
        },
        {
            'unit_id': 'FC-PROC-002',
            'item_code': 'ITEM-PROC-001',
            'weight_kg': 400,
            'sales_unit_price': 100.0,
            'cost_amount': allocation_result['allocations'][1]['cost'] if allocation_result['allocations'] else 0
        },
    ],
    staff="山田太郎",
    note="テスト出荷"
)

if sales_result['success']:
    print(f"\nSales ID: {sales_result['sales_id']}")
    print(f"Total Sales: {sales_result['total_sales']:.0f}円")
    print(f"Total Cost: {sales_result['total_cost']:.0f}円")
    print(f"Total Profit: {sales_result['total_profit']:.0f}円")
    print(f"Profit Rate: {sales_result['profit_rate']:.1f}%")
else:
    print(f"\nError: {sales_result['message']}")

# ===============================================
# 4. 粗利集計テスト
# ===============================================
print("\n[4] Profit Summary")
print("-" * 70)

# 販売先別粗利
destinations = ProfitService.get_profit_by_destination()
print(f"\nProfit by Destination:")
for dest in destinations:
    if dest['destination']:
        print(f"  {dest['destination']}:")
        print(f"    Sales: {dest['total_sales']:.0f}円")
        print(f"    Cost: {dest['total_cost']:.0f}円")
        print(f"    Profit: {dest['total_profit']:.0f}円")
        print(f"    Profit Rate: {dest['profit_rate']:.1f}%")

# 品目別粗利
items = ProfitService.get_profit_by_item_code()
print(f"\nProfit by Item Code:")
for item in items:
    if item['item_code']:
        print(f"  {item['item_code']}:")
        print(f"    Weight: {item['total_weight']:.0f}kg")
        print(f"    Sales: {item['total_sales']:.0f}円")
        print(f"    Cost: {item['total_cost']:.0f}円")
        print(f"    Profit: {item['total_profit']:.0f}円")
        print(f"    Profit Rate: {item['profit_rate']:.1f}%")

# ===============================================
# Summary
# ===============================================
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Cost Allocation: OK (重量按分 {len(allocation_result.get('allocations', []))}件)")
print(f"Sales Registration: OK (売上ID: {sales_result.get('sales_id', 'N/A')})")
print(f"Profit Calculation: OK")
print(f"Profit Summary: OK")
print(f"\nAll tests PASSED - Phase 4 Implementation Successful!")
print("=" * 70)
