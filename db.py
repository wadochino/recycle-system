"""
データベース層
SQLite 対応版（Streamlit Cloud 用）
"""

import sqlite3
from contextlib import contextmanager

DB_FILE = "inventory.db"

@contextmanager
def get_conn():
    """SQLite コンテキストマネージャー"""
    conn = sqlite3.connect(DB_FILE)
    conn.isolation_level = None
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """データベース初期化"""
    with get_conn() as conn:
        cur = conn.cursor()

        # Phase 1: 在庫テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id TEXT UNIQUE,
                internal_id TEXT,
                customer TEXT,
                material TEXT,
                color TEXT,
                shape TEXT,
                package TEXT,
                weight_kg REAL,
                location TEXT,
                status TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cost_amount REAL DEFAULT 0
            )
        """)

        # Phase 1: 受付テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT UNIQUE,
                internal_id TEXT,
                receipt_date TEXT,
                customer TEXT,
                material TEXT,
                color TEXT,
                shape TEXT,
                package TEXT,
                planned_qty INTEGER,
                location TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: 履歴テーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id TEXT,
                operation TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: 移動ログ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS move_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id TEXT,
                move_date TEXT,
                from_location TEXT,
                to_location TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: アイテムパターン
        cur.execute("""
            CREATE TABLE IF NOT EXISTS item_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: マスタテーブル
        cur.execute("""
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: 処理ロット
        cur.execute("""
            CREATE TABLE IF NOT EXISTS process_lots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id TEXT UNIQUE,
                internal_id TEXT,
                process_date TEXT,
                inputs TEXT,
                outputs TEXT,
                loss_kg REAL,
                loss_rate REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 3: 品目マスタ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS item_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT UNIQUE,
                item_name TEXT,
                category TEXT,
                unit TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 3: 仕入単価履歴
        cur.execute("""
            CREATE TABLE IF NOT EXISTS purchase_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT,
                unit_price REAL,
                effective_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_code) REFERENCES item_codes(item_code)
            )
        """)

        # Phase 3: 販売単価履歴
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_code TEXT,
                unit_price REAL,
                effective_date TEXT,
                end_date TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (item_code) REFERENCES item_codes(item_code)
            )
        """)

        # Phase 3: サイト・拠点
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_code TEXT UNIQUE,
                site_name TEXT,
                address TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 3: 保管場所（拠点配下）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location_code TEXT UNIQUE,
                location_name TEXT,
                site_id INTEGER,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            )
        """)

        # Phase 4: 在庫原価
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_cost (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id TEXT UNIQUE,
                item_code TEXT,
                purchase_unit_price REAL,
                purchase_amount REAL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES inventory(unit_id)
            )
        """)

        # Phase 4: 売上ヘッダ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales_headers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_id TEXT UNIQUE,
                internal_id TEXT,
                ship_date TEXT,
                destination TEXT,
                staff TEXT,
                notes TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 4: 売上明細
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_id TEXT,
                internal_id TEXT,
                unit_id TEXT,
                item_code TEXT,
                weight_kg REAL,
                sales_unit_price REAL,
                sales_amount REAL,
                cost_amount REAL,
                profit REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sales_id) REFERENCES sales_headers(sales_id)
            )
        """)

        # Phase 5: ユーザー
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 5: ユーザー権限
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                UNIQUE(username, role),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """)

        # Phase 5: 監査ログ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT,
                action TEXT,
                table_name TEXT,
                record_id TEXT,
                detail TEXT,
                ip_address TEXT,
                status TEXT DEFAULT 'success'
            )
        """)

        # Phase 5: QRコード管理
        cur.execute("""
            CREATE TABLE IF NOT EXISTS qrcode_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unit_id TEXT UNIQUE,
                qrcode_data TEXT,
                qrcode_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✓ Database initialized successfully")

def migrate_phase5_add_columns():
    """Phase 5 マイグレーション"""
    print("[Migration] Phase 5 tables already included in init_db()")

def migrate_phase4_add_columns():
    """Phase 4 マイグレーション"""
    print("[Migration] Phase 4 tables already included in init_db()")

def migrate_phase3_add_columns():
    """Phase 3 マイグレーション"""
    print("[Migration] Phase 3 tables already included in init_db()")

def migrate_add_internal_ids():
    """内部IDマイグレーション"""
    print("[Migration] Internal ID columns already included in init_db()")

# ===== 既存の関数互換性 =====

def get_inventory_rows():
    """在庫一覧を取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        cur.execute("SELECT * FROM inventory ORDER BY created_at DESC")
        return cur.fetchall()

def insert_inventory_row(row):
    """在庫を追加"""
    query = """
        INSERT INTO inventory
        (unit_id, customer, material, color, shape, package, weight_kg, location, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, (
            row.get("在庫単位ID"),
            row.get("取引先"),
            row.get("樹脂"),
            row.get("色"),
            row.get("形状"),
            row.get("荷姿"),
            float(row.get("重量kg", 0)),
            row.get("保管場所"),
            row.get("状態"),
            row.get("備考")
        ))
        conn.commit()

def insert_receipt_row(row):
    """受付を追加"""
    query = """
        INSERT INTO receipts
        (receipt_id, receipt_date, customer, material, color, shape, package, planned_qty, location, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, (
            row.get("受付ID"),
            row.get("日付"),
            row.get("取引先"),
            row.get("樹脂"),
            row.get("色"),
            row.get("形状"),
            row.get("荷姿"),
            int(row.get("予定数量", 0)),
            row.get("保管場所"),
            row.get("状態")
        ))
        conn.commit()

def get_pending_receipts():
    """予定済み受付を取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        cur.execute("SELECT * FROM receipts WHERE status = '予定' ORDER BY receipt_date DESC")
        return cur.fetchall()

def get_next_receipt_id():
    """次の受付IDを取得"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM receipts")
        count = cur.fetchone()[0]
        return f"R-{count + 1:04d}"

def update_receipt_status(receipt_id, status):
    """受付ステータスを更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE receipts SET status = ? WHERE receipt_id = ?", (status, receipt_id))
        conn.commit()

def get_next_unit_id(package, count):
    """次の在庫単位IDを取得"""
    prefix_map = {
        "フレコン": "FC",
        "メッシュボックス": "MB",
        "カゴ": "KG",
        "パレット積み": "PL",
        "紙袋": "BG",
        "ロール": "RL",
        "その他": "OT",
    }
    prefix = prefix_map.get(package, "OT")
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM inventory WHERE package = ?", (package,))
        next_num = cur.fetchone()[0] + 1
        return f"{prefix}-{next_num:04d}"

def update_inventory_status(unit_id, status):
    """在庫ステータスを更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE inventory SET status = ? WHERE unit_id = ?", (status, unit_id))
        conn.commit()

def update_inventory_location(unit_id, location):
    """在庫保管場所を更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE inventory SET location = ? WHERE unit_id = ?", (location, unit_id))
        conn.commit()

def insert_history(unit_id, operation, details=""):
    """履歴を記録"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO history (unit_id, operation, details) VALUES (?, ?, ?)",
                   (unit_id, operation, details))
        conn.commit()

def get_history_rows():
    """履歴を取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        cur.execute("SELECT * FROM history ORDER BY created_at DESC")
        return cur.fetchall()

def get_master_items(category):
    """マスタアイテムを取得"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM masters WHERE category = ? AND is_active = 1 ORDER BY sort_order", (category,))
        rows = cur.fetchall()
        return [row[0] for row in rows]

def insert_master_item(category, name):
    """マスタアイテムを追加"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM masters WHERE category = ? AND name = ?", (category, name))
        if cur.fetchone():
            return
        cur.execute("SELECT MAX(sort_order) FROM masters WHERE category = ?", (category,))
        max_order = cur.fetchone()[0] or 0
        cur.execute("INSERT INTO masters (category, name, sort_order) VALUES (?, ?, ?)",
                   (category, name, max_order + 10))
        conn.commit()

def get_master_items_with_order(category):
    """ソート順付きマスタアイテムを取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        cur.execute("SELECT name, sort_order FROM masters WHERE category = ? AND is_active = 1 ORDER BY sort_order", (category,))
        return cur.fetchall()

def update_master_sort_orders(category, order_dict):
    """マスタアイテムのソート順を一括更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        for name, order in order_dict.items():
            cur.execute("UPDATE masters SET sort_order = ? WHERE category = ? AND name = ?",
                       (order, category, name))
        conn.commit()

def deactivate_master_item(category, name):
    """マスタアイテムを無効化"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE masters SET is_active = 0 WHERE category = ? AND name = ?", (category, name))
        conn.commit()

def get_item_patterns(category=None):
    """アイテムパターンを取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        if category:
            cur.execute("SELECT * FROM item_patterns WHERE category = ? AND is_active = 1 ORDER BY sort_order", (category,))
        else:
            cur.execute("SELECT * FROM item_patterns WHERE is_active = 1 ORDER BY category, sort_order")
        return cur.fetchall()

def insert_item_pattern(category, name):
    """アイテムパターンを追加"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO item_patterns (category, name) VALUES (?, ?)", (category, name))
        conn.commit()

def get_next_process_lot_id():
    """次の処理ロットIDを取得"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as cnt FROM process_lots")
        count = cur.fetchone()[0]
        return f"LOT-{count + 1:04d}"

def insert_process_lot(lot_id, process_date, inputs, outputs, loss_kg, loss_rate, notes=""):
    """処理ロットを追加"""
    query = """
        INSERT INTO process_lots
        (lot_id, process_date, inputs, outputs, loss_kg, loss_rate, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, (lot_id, process_date, inputs, outputs, loss_kg, loss_rate, notes))
        conn.commit()

def get_process_lots():
    """処理ロット一覧を取得"""
    with get_conn() as conn:
        conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
        cur = conn.cursor()
        cur.execute("SELECT * FROM process_lots ORDER BY created_at DESC")
        return cur.fetchall()
