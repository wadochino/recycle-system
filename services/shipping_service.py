"""
出荷処理サービス
- 出荷登録
- トランザクション管理
"""

from datetime import datetime
from db import (
    get_conn,
    update_inventory_status,
    insert_history,
)

class ShippingService:
    """出荷処理を管理するサービス"""

    @staticmethod
    def register_shipping(
        selected_ids,
        ship_date,
        destination,
        note="",
    ):
        """
        出荷登録（複数在庫を一括）

        Args:
            selected_ids: 出荷対象在庫ID（文字列リスト）
            ship_date: 出荷日
            destination: 出荷先
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

                for unit_id in selected_ids:
                    # 出荷済ステータスに更新
                    cur.execute("""
                        UPDATE inventory
                        SET status = ?, notes = ?
                        WHERE unit_id = ?
                    """, (
                        "出荷済",
                        f"出荷日:{ship_date} / 出荷先:{destination} / {note}",
                        unit_id
                    ))

                    # 出荷履歴を記録
                    cur.execute("""
                        INSERT INTO history (
                            unit_id,
                            operation,
                            details
                        )
                        VALUES (?, ?, ?)
                    """, (
                        unit_id,
                        "出荷",
                        f"出荷先:{destination} / {note}"
                    ))

                conn.commit()

                return {
                    'success': True,
                    'count': len(selected_ids),
                    'message': f"{len(selected_ids)}件を出荷登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'count': 0,
                    'message': f"エラー：{str(e)}"
                }
