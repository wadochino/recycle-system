import csv
import os
from db import get_conn, init_db

init_db()

def read_csv_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

conn = get_conn()
cur = conn.cursor()

# inventory
for r in read_csv_file("data.csv"):
    cur.execute("""
        INSERT OR IGNORE INTO inventory
        (date, customer, material, color, shape, package, unit_id, parent_id, weight_kg, location, status, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r.get("日付", ""),
        r.get("取引先", ""),
        r.get("樹脂", ""),
        r.get("色", ""),
        r.get("形状", ""),
        r.get("荷姿", ""),
        r.get("在庫単位ID", ""),
        r.get("親ID", ""),
        int(float(r.get("重量kg", 0) or 0)),
        r.get("保管場所", ""),
        r.get("状態", ""),
        r.get("備考", ""),
    ))

# receipts
for r in read_csv_file("receipts.csv"):
    cur.execute("""
        INSERT OR IGNORE INTO receipts
        (receipt_id, date, customer, material, color, shape, package, planned_qty, location, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r.get("受付ID", ""),
        r.get("日付", ""),
        r.get("取引先", ""),
        r.get("樹脂", ""),
        r.get("色", ""),
        r.get("形状", ""),
        r.get("荷姿", ""),
        int(float(r.get("予定数量", 0) or 0)),
        r.get("保管場所", ""),
        r.get("状態", ""),
    ))

# move logs
for r in read_csv_file("move_log.csv"):
    cur.execute("""
        INSERT INTO move_logs
        (date, unit_id, from_location, to_location, note)
        VALUES (?, ?, ?, ?, ?)
    """, (
        r.get("日付", ""),
        r.get("在庫単位ID", ""),
        r.get("移動前", ""),
        r.get("移動後", ""),
        r.get("備考", ""),
    ))

# patterns
for r in read_csv_file("patterns.csv"):
    cur.execute("""
        INSERT INTO item_patterns
        (customer, material, color, shape, package)
        VALUES (?, ?, ?, ?, ?)
    """, (
        r.get("取引先", ""),
        r.get("樹脂", ""),
        r.get("色", ""),
        r.get("形状", ""),
        r.get("荷姿", ""),
    ))

conn.commit()
conn.close()

print("CSVからSQLiteへの移行が完了しました。")