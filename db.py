"""
データベース層
PostgreSQL 対応版（Render + Streamlit Cloud 用）
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import os

# 環境変数から接続文字列を取得
DATABASE_URL = os.environ.get('DATABASE_URL')

@contextmanager
def get_conn():
    """PostgreSQL コンテキストマネージャー"""
    conn = psycopg2.connect(DATABASE_URL)
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                unit_id TEXT,
                operation TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Phase 1: 移動ログ
        cur.execute("""
            CREATE TABLE IF NOT EXISTS move_logs (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                lot_id TEXT UNIQUE,
                internal_id TEXT,
                process_date TEXT,
                process TEXT,
                input_ids TEXT,
                output_ids TEXT,
                input_weight REAL,
                output_weight REAL,
                loss_weight REAL,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                unit_id TEXT UNIQUE,
                qrcode_data TEXT,
                qrcode_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✓ PostgreSQL Database initialized successfully")

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
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                unit_id, internal_id, customer, material, color, shape, package,
                weight_kg, location, status, notes, cost_amount,
                (created_at AT TIME ZONE 'Asia/Tokyo')::text as created_at,
                (updated_at AT TIME ZONE 'Asia/Tokyo')::text as updated_at
            FROM inventory
            ORDER BY created_at ASC
        """)
        rows = cur.fetchall()

        # 英語カラムを日本語にマッピング
        col_map = {
            'unit_id': '在庫単位ID',
            'internal_id': '親ID',
            'customer': '取引先',
            'material': '樹脂',
            'color': '色',
            'shape': '形状',
            'package': '荷姿',
            'weight_kg': '重量kg',
            'location': '保管場所',
            'status': '状態',
            'notes': '備考',
            'created_at': '日付',
            'updated_at': '更新日時',
            'cost_amount': '原価金額'
        }

        return [{col_map.get(k, k): v for k, v in row.items()} for row in rows]

def insert_inventory_row(row):
    """在庫を追加（重複チェック付き）"""
    unit_id = row.get("在庫単位ID")

    with get_conn() as conn:
        cur = conn.cursor()

        # 既に存在するかチェック
        cur.execute("SELECT COUNT(*) FROM inventory WHERE unit_id = %s", (unit_id,))
        if cur.fetchone()[0] > 0:
            return  # 既に存在する場合はスキップ

        query = """
            INSERT INTO inventory
            (unit_id, internal_id, customer, material, color, shape, package, weight_kg, location, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (
            unit_id,
            row.get("親ID"),
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
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM receipts WHERE status = '予定' ORDER BY receipt_date DESC")
        rows = cur.fetchall()

        # 英語カラムを日本語にマッピング
        col_map = {
            'receipt_id': '受付ID',
            'internal_id': '内部ID',
            'receipt_date': '日付',
            'customer': '取引先',
            'material': '樹脂',
            'color': '色',
            'shape': '形状',
            'package': '荷姿',
            'planned_qty': '予定数量',
            'location': '保管場所',
            'status': '状態',
            'created_at': '作成日時'
        }

        return [{col_map.get(k, k): v for k, v in row.items()} for row in rows]

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
        cur.execute("UPDATE receipts SET status = %s WHERE receipt_id = %s", (status, receipt_id))
        conn.commit()

def get_next_unit_id(package, count):
    """次の在庫単位IDを取得（ループ内での連番対応）"""
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
        cur.execute("SELECT COUNT(*) as cnt FROM inventory WHERE package = %s", (package,))
        db_count = cur.fetchone()[0]
        # count パラメータ（ループ内インデックス）を使用して、一意な ID を生成
        next_num = db_count + count + 1
        return f"{prefix}-{next_num:04d}"

def update_inventory_status(unit_id, status):
    """在庫ステータスを更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE inventory SET status = %s WHERE unit_id = %s", (status, unit_id))
        conn.commit()

def update_inventory_location(unit_id, location):
    """在庫保管場所を更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE inventory SET location = %s WHERE unit_id = %s", (location, unit_id))
        conn.commit()

def update_inventory_row_fields(unit_id, updates):
    """在庫情報を更新（複数フィールド対応）"""
    if not updates:
        return

    # 日本語キーから英語カラム名へのマッピング
    col_map = {
        '取引先': 'customer',
        '樹脂': 'material',
        '色': 'color',
        '形状': 'shape',
        '荷姿': 'package',
        '重量kg': 'weight_kg',
        '保管場所': 'location',
        '状態': 'status',
        '備考': 'notes',
    }

    with get_conn() as conn:
        cur = conn.cursor()

        # 更新するカラムと値を構築
        set_parts = []
        values = []
        for jp_col in updates.keys():
            if jp_col in col_map:
                set_parts.append(f"{col_map[jp_col]} = %s")
                values.append(updates[jp_col])

        if set_parts:
            values.append(unit_id)
            set_clause = ", ".join(set_parts)
            query = f"UPDATE inventory SET {set_clause} WHERE unit_id = %s"
            cur.execute(query, values)
            conn.commit()

def insert_history(unit_id, operation, details=""):
    """履歴を記録"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO history (unit_id, operation, details) VALUES (%s, %s, %s)",
                   (unit_id, operation, details))
        conn.commit()

def get_history_rows():
    """履歴を取得"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM history ORDER BY created_at DESC")
        rows = cur.fetchall()

        # 英語カラムを日本語にマッピング
        col_map = {
            'unit_id': '在庫単位ID',
            'operation': '操作',
            'details': '詳細',
            'created_at': '作成日時'
        }

        return [{col_map.get(k, k): v for k, v in row.items()} for row in rows]

def get_master_items(category):
    """マスタアイテムを取得"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM masters WHERE category = %s AND is_active = 1 ORDER BY sort_order", (category,))
        rows = cur.fetchall()
        return [row[0] for row in rows]

def insert_master_item(category, name):
    """マスタアイテムを追加"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM masters WHERE category = %s AND name = %s", (category, name))
        if cur.fetchone():
            return
        cur.execute("SELECT MAX(sort_order) FROM masters WHERE category = %s", (category,))
        max_order = cur.fetchone()[0] or 0
        cur.execute("INSERT INTO masters (category, name, sort_order) VALUES (%s, %s, %s)",
                   (category, name, max_order + 10))
        conn.commit()

def get_master_items_with_order(category):
    """ソート順付きマスタアイテムを取得"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, sort_order FROM masters WHERE category = %s AND is_active = 1 ORDER BY sort_order", (category,))
        return cur.fetchall()

def update_master_sort_orders(category, order_dict):
    """マスタアイテムのソート順を一括更新"""
    with get_conn() as conn:
        cur = conn.cursor()
        for name, order in order_dict.items():
            cur.execute("UPDATE masters SET sort_order = %s WHERE category = %s AND name = %s",
                       (order, category, name))
        conn.commit()

def deactivate_master_item(category, name):
    """マスタアイテムを無効化"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE masters SET is_active = 0 WHERE category = %s AND name = %s", (category, name))
        conn.commit()

def get_item_patterns(category=None):
    """アイテムパターンを取得"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if category:
            cur.execute("SELECT * FROM item_patterns WHERE category = %s AND is_active = 1 ORDER BY sort_order", (category,))
        else:
            cur.execute("SELECT * FROM item_patterns WHERE is_active = 1 ORDER BY category, sort_order")
        return cur.fetchall()

def insert_item_pattern(category, name):
    """アイテムパターンを追加"""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO item_patterns (category, name) VALUES (%s, %s)", (category, name))
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
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(query, (lot_id, process_date, inputs, outputs, loss_kg, loss_rate, notes))
        conn.commit()

def get_shipped_inventory():
    """出荷済み在庫（出荷実績）を取得"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM inventory WHERE status = '出荷済' ORDER BY updated_at DESC")
        rows = cur.fetchall()

        # 英語カラムを日本語にマッピング
        col_map = {
            'unit_id': '在庫単位ID',
            'internal_id': '親ID',
            'customer': '取引先',
            'material': '樹脂',
            'color': '色',
            'shape': '形状',
            'package': '荷姿',
            'weight_kg': '重量kg',
            'location': '保管場所',
            'status': '状態',
            'notes': '備考',
            'created_at': '作成日時',
            'updated_at': '更新日時',
            'cost_amount': '原価金額'
        }

        return [{col_map.get(k, k): v for k, v in row.items()} for row in rows]

def get_process_lots():
    """処理ロット一覧を取得"""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM process_lots ORDER BY created_at DESC")
        rows = cur.fetchall()

        # 英語カラムを日本語にマッピング
        col_map = {
            'lot_id': 'ロットID',
            'internal_id': '内部ID',
            'process_date': '処理日付',
            'inputs': '投入',
            'outputs': '産出',
            'loss_kg': '損失kg',
            'loss_rate': '損失率',
            'notes': '備考',
            'created_at': '作成日時'
        }

        return [{col_map.get(k, k): v for k, v in row.items()} for row in rows]
