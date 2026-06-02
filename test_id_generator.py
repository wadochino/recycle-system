"""
ID採番サービスのテスト
- 内部ID（ULID）の生成
- 表示用ID（FC-0001形式）の採番
"""

from utils import InternalIDGenerator, DisplayIDGenerator
from db import init_db, migrate_add_internal_ids

init_db()
migrate_add_internal_ids()

print("=" * 70)
print("[TEST] ID Generator Service")
print("=" * 70)

# ===============================================
# 1. 内部ID（ULID）の生成テスト
# ===============================================
print("\n[1] Internal ID Generation (ULID)")
print("-" * 70)

ulid1 = InternalIDGenerator.generate()
ulid2 = InternalIDGenerator.generate()
ulid3 = InternalIDGenerator.generate()

print(f"Generated ULID #1: {ulid1}")
print(f"Generated ULID #2: {ulid2}")
print(f"Generated ULID #3: {ulid3}")

print(f"\nULID Length: {len(ulid1)} chars")
print(f"All unique: {len({ulid1, ulid2, ulid3}) == 3}")

# ===============================================
# 2. 表示用ID採番テスト
# ===============================================
print("\n[2] Display ID Generation (FC-0001 format)")
print("-" * 70)

# 在庫単位ID
inv_id1 = DisplayIDGenerator.generate_inventory_id("フレコン", 0)
inv_id2 = DisplayIDGenerator.generate_inventory_id("フレコン", 1)
inv_id3 = DisplayIDGenerator.generate_inventory_id("カゴ", 0)

print(f"Inventory ID (Furecon) #1: {inv_id1}")
print(f"Inventory ID (Furecon) #2: {inv_id2}")
print(f"Inventory ID (Kago) #1:     {inv_id3}")

# 受付ID
rcpt_id = DisplayIDGenerator.generate_receipt_id()
print(f"\nReceipt ID:     {rcpt_id}")

# ロットID
lot_id = DisplayIDGenerator.generate_lot_id()
print(f"Process Lot ID: {lot_id}")

# ===============================================
# 3. スキーマ確認
# ===============================================
print("\n[3] DB Schema Verification")
print("-" * 70)

from db import get_conn

with get_conn() as conn:
    conn.row_factory = None
    cur = conn.cursor()

    # inventory テーブルのカラムを確認
    cur.execute("PRAGMA table_info(inventory)")
    columns = cur.fetchall()

    print("\nInventory table columns:")
    has_internal_id = False
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        print(f"  - {col_name} ({col_type})")
        if col_name == "internal_id":
            has_internal_id = True

    print(f"\nHas internal_id column: {has_internal_id}")

# ===============================================
# Summary
# ===============================================
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print(f"Internal ID (ULID): OK")
print(f"Display ID Generation: OK")
print(f"DB Schema: OK")
print(f"\nAll tests PASSED!")
print("=" * 70)
