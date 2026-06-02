"""
在庫管理サービス
- 在庫移動
- 状態変更
- トランザクション管理
"""

from datetime import datetime
from db import (
    get_conn,
    update_inventory_status,
    update_inventory_location,
    insert_history,
)

class InventoryService:
    """在庫管理を担当するサービス"""

    @staticmethod
    def move_inventory(
        selected_rows,
        new_location,
        note="",
    ):
        """
        在庫を一括移動

        Args:
            selected_rows: 移動対象在庫リスト（辞書）
            new_location: 移動先場所
            note: 備考

        Returns:
            dict: {
                'success': bool,
                'count': int,
                'message': str
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                for r in selected_rows:
                    old_location = r["保管場所"]
                    unit_id = r["在庫単位ID"]

                    # 保管場所を更新
                    cur.execute("""
                        UPDATE inventory
                        SET location = ?, note = ?
                        WHERE unit_id = ?
                    """, (
                        new_location,
                        f"移動: {old_location} → {new_location} / {note}",
                        unit_id
                    ))

                    # 移動履歴を記録
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
                        unit_id,
                        "在庫移動",
                        f"{old_location} → {new_location} / {note}",
                        int(r["重量kg"])
                    ))

                conn.commit()

                return {
                    'success': True,
                    'count': len(selected_rows),
                    'message': f"{len(selected_rows)}件を {new_location} に移動しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'count': 0,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def change_status(
        unit_id,
        old_status,
        new_status,
        note="",
    ):
        """
        在庫の状態を変更（誤登録・廃棄・返品など）

        Args:
            unit_id: 在庫単位ID
            old_status: 変更前の状態
            new_status: 変更後の状態
            note: 理由・備考

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                # ステータスを更新
                cur.execute("""
                    UPDATE inventory
                    SET status = ?, note = ?
                    WHERE unit_id = ?
                """, (
                    new_status,
                    f"状態変更: {old_status} → {new_status} / {note}",
                    unit_id
                ))

                # 状態変更履歴を記録
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
                    unit_id,
                    "状態変更",
                    f"{old_status} → {new_status} / {note}",
                    0
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"{unit_id} を {new_status} に変更しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }
