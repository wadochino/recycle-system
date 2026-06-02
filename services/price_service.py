"""
価格管理サービス
- 仕入単価履歴の管理
- 販売単価履歴の管理
- 有効な単価の取得
"""

from datetime import date
from db import get_conn

class PriceService:
    """仕入・販売単価を管理するサービス"""

    @staticmethod
    def register_purchase_price(
        item_code,
        customer,
        start_date,
        end_date,
        purchase_unit_price,
        note="",
    ):
        """
        仕入単価を登録

        Args:
            item_code: 品目コード
            customer: 取引先
            start_date: 適用開始日
            end_date: 適用終了日（Noneで無期限）
            purchase_unit_price: 仕入単価
            note: 備考

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

                cur.execute("""
                    INSERT INTO purchase_price_history (
                        item_code,
                        customer,
                        start_date,
                        end_date,
                        purchase_unit_price,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item_code,
                    customer,
                    str(start_date),
                    str(end_date) if end_date else None,
                    float(purchase_unit_price),
                    note,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"仕入単価を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_current_purchase_price(item_code, customer, target_date=None):
        """
        有効な仕入単価を取得

        Args:
            item_code: 品目コード
            customer: 取引先
            target_date: 対象日（デフォルト：本日）

        Returns:
            float or None: 仕入単価、見つからない場合は None
        """
        if target_date is None:
            target_date = date.today()

        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT purchase_unit_price
                FROM purchase_price_history
                WHERE item_code = ?
                  AND customer = ?
                  AND start_date <= ?
                  AND (end_date IS NULL OR end_date >= ?)
                  AND is_active = 1
                ORDER BY start_date DESC
                LIMIT 1
            """, (
                item_code,
                customer,
                str(target_date),
                str(target_date),
            ))

            row = cur.fetchone()

        return row[0] if row else None

    @staticmethod
    def register_sales_price(
        item_code,
        destination,
        start_date,
        end_date,
        sales_unit_price,
        note="",
    ):
        """
        販売単価を登録

        Args:
            item_code: 品目コード
            destination: 販売先
            start_date: 適用開始日
            end_date: 適用終了日（Noneで無期限）
            sales_unit_price: 販売単価
            note: 備考

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

                cur.execute("""
                    INSERT INTO sales_price_history (
                        item_code,
                        destination,
                        start_date,
                        end_date,
                        sales_unit_price,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    item_code,
                    destination,
                    str(start_date),
                    str(end_date) if end_date else None,
                    float(sales_unit_price),
                    note,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"販売単価を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_current_sales_price(item_code, destination, target_date=None):
        """
        有効な販売単価を取得

        Args:
            item_code: 品目コード
            destination: 販売先
            target_date: 対象日（デフォルト：本日）

        Returns:
            float or None: 販売単価、見つからない場合は None
        """
        if target_date is None:
            target_date = date.today()

        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT sales_unit_price
                FROM sales_price_history
                WHERE item_code = ?
                  AND destination = ?
                  AND start_date <= ?
                  AND (end_date IS NULL OR end_date >= ?)
                  AND is_active = 1
                ORDER BY start_date DESC
                LIMIT 1
            """, (
                item_code,
                destination,
                str(target_date),
                str(target_date),
            ))

            row = cur.fetchone()

        return row[0] if row else None
