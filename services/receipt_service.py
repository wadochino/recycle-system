"""
入荷予定・計量登録サービス
- 予定登録
- 計量登録（予定あり/なし）
- トランザクション管理
"""

from datetime import datetime
from db import (
    get_conn,
    get_next_receipt_id,
    get_next_unit_id,
    insert_inventory_row,
    insert_history,
    update_receipt_status,
)

class ReceiptService:
    """入荷予定・計量を管理するサービス"""

    @staticmethod
    def register_planned_receipt(receipt_date, customer, material, package, planned_qty, location):
        """
        入荷予定を登録

        Args:
            receipt_date: 予定日
            customer: 取引先コード
            material: 樹脂
            package: 荷姿
            planned_qty: 予定数量
            location: 保管予定場所

        Returns:
            str: 受付ID
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                receipt_id = get_next_receipt_id()

                cur.execute("""
                    INSERT INTO receipts (
                        receipt_id,
                        date,
                        customer,
                        material,
                        color,
                        shape,
                        package,
                        planned_qty,
                        location,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    receipt_id,
                    str(receipt_date),
                    customer,
                    material,
                    "",
                    "",
                    package,
                    int(planned_qty),
                    location,
                    "予定",
                ))

                conn.commit()
                return receipt_id

            except Exception as e:
                conn.rollback()
                raise e

    @staticmethod
    def register_weighing_no_plan(
        customer,
        material,
        color,
        shape,
        package,
        location,
        weights,
    ):
        """
        計量登録（予定なし）

        Args:
            customer: 取引先コード
            material: 樹脂
            color: 色
            shape: 形状
            package: 荷姿
            location: 保管場所
            weights: 重量リスト（整数）

        Returns:
            dict: {
                'success': bool,
                'new_ids': list[str],
                'message': str
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                new_ids = []

                for i, w in enumerate(weights):
                    new_id = get_next_unit_id(package, i)
                    new_ids.append(new_id)

                    cur.execute("""
                        INSERT INTO inventory (
                            date,
                            customer,
                            material,
                            color,
                            shape,
                            package,
                            unit_id,
                            parent_id,
                            weight_kg,
                            location,
                            status,
                            note
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        customer,
                        material,
                        color,
                        shape,
                        package,
                        new_id,
                        "",
                        int(w),
                        location,
                        "原料在庫",
                        "予定なし登録"
                    ))

                    # 計量履歴を記録
                    cur.execute("""
                        INSERT INTO inventory_history (
                            date,
                            unit_id,
                            action,
                            detail,
                            weight_kg
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        new_id,
                        "計量登録",
                        f"{customer} / {material} / {w}kg",
                        int(w)
                    ))

                conn.commit()

                return {
                    'success': True,
                    'new_ids': new_ids,
                    'message': f"{len(new_ids)}件登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'new_ids': [],
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def register_weighing_with_plan(
        receipt,
        color,
        shape,
        weights,
    ):
        """
        計量登録（予定あり）

        Args:
            receipt: 入荷予定（辞書）
            color: 色
            shape: 形状
            weights: 重量リスト（整数）

        Returns:
            dict: {
                'success': bool,
                'new_ids': list[str],
                'message': str
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                new_ids = []

                for i, w in enumerate(weights):
                    new_id = get_next_unit_id(receipt["荷姿"], i)
                    new_ids.append(new_id)

                    cur.execute("""
                        INSERT INTO inventory (
                            date,
                            customer,
                            material,
                            color,
                            shape,
                            package,
                            unit_id,
                            parent_id,
                            weight_kg,
                            location,
                            status,
                            note
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        receipt["日付"],
                        receipt["取引先"],
                        receipt["樹脂"],
                        color,
                        shape,
                        receipt["荷姿"],
                        new_id,
                        "",
                        int(w),
                        receipt["保管場所"],
                        "原料在庫",
                        f"受付ID:{receipt['受付ID']}"
                    ))

                    # 計量履歴を記録
                    cur.execute("""
                        INSERT INTO inventory_history (
                            date,
                            unit_id,
                            action,
                            detail,
                            weight_kg
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        new_id,
                        "計量登録",
                        f"{receipt['取引先']} / {receipt['樹脂']} / {w}kg",
                        int(w)
                    ))

                # 予定ステータスを計量済に更新
                cur.execute("""
                    UPDATE receipts
                    SET status = ?
                    WHERE receipt_id = ?
                """, (
                    "計量済",
                    receipt["受付ID"]
                ))

                conn.commit()

                return {
                    'success': True,
                    'new_ids': new_ids,
                    'message': f"{len(new_ids)}件登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'new_ids': [],
                    'message': f"エラー：{str(e)}"
                }
