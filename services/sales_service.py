"""
売上管理サービス
- 売上登録（ヘッダ・明細）
- 販売単価の自動取得
- 売上金額の自動計算
- トランザクション管理
"""

from datetime import datetime
from db import get_conn
from services import PriceService
from utils import InternalIDGenerator

class SalesService:
    """売上を管理するサービス"""

    @staticmethod
    def register_sales(
        ship_date,
        destination,
        items,
        staff="",
        note="",
    ):
        """
        売上を登録（ヘッダ・明細）

        Args:
            ship_date: 出荷日
            destination: 出荷先
            items: 売上明細リスト
                [
                    {
                        'unit_id': str,
                        'item_code': str,
                        'weight_kg': float,
                        'sales_unit_price': float (オプション),
                        'cost_amount': float (オプション)
                    },
                    ...
                ]
            staff: 担当者
            note: 備考

        Returns:
            dict: {
                'success': bool,
                'sales_id': str,
                'total_sales': float,
                'total_cost': float,
                'total_profit': float,
                'message': str
            }
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                # 売上IDを採番
                sales_id = SalesService._generate_sales_id(cur)

                # ヘッダを挿入
                internal_id = InternalIDGenerator.generate()

                cur.execute("""
                    INSERT INTO sales_headers (
                        sales_id,
                        ship_date,
                        destination,
                        staff,
                        note,
                        status,
                        created_at,
                        internal_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    sales_id,
                    str(ship_date),
                    destination,
                    staff,
                    note,
                    'completed',
                    datetime.now().isoformat(),
                    internal_id,
                ))

                # 明細を挿入・計算
                total_sales = 0.0
                total_cost = 0.0
                total_profit = 0.0

                for item in items:
                    unit_id = item['unit_id']
                    item_code = item['item_code']
                    weight_kg = float(item['weight_kg'])
                    cost_amount = float(item.get('cost_amount', 0) or 0)

                    # 販売単価を取得または指定
                    if 'sales_unit_price' in item and item['sales_unit_price']:
                        sales_unit_price = float(item['sales_unit_price'])
                    else:
                        # システムから有効な販売単価を取得
                        sales_unit_price = PriceService.get_current_sales_price(
                            item_code,
                            destination,
                            ship_date
                        ) or 0.0

                    # 売上金額を計算
                    sales_amount = weight_kg * sales_unit_price

                    # 粗利を計算
                    profit = sales_amount - cost_amount

                    total_sales += sales_amount
                    total_cost += cost_amount
                    total_profit += profit

                    # 明細を挿入
                    detail_internal_id = InternalIDGenerator.generate()

                    cur.execute("""
                        INSERT INTO sales_details (
                            sales_id,
                            unit_id,
                            item_code,
                            weight_kg,
                            sales_unit_price,
                            sales_amount,
                            cost_amount,
                            profit,
                            internal_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        sales_id,
                        unit_id,
                        item_code,
                        weight_kg,
                        sales_unit_price,
                        sales_amount,
                        cost_amount,
                        profit,
                        detail_internal_id,
                    ))

                conn.commit()

                return {
                    'success': True,
                    'sales_id': sales_id,
                    'total_sales': total_sales,
                    'total_cost': total_cost,
                    'total_profit': total_profit,
                    'profit_rate': (total_profit / total_sales * 100) if total_sales > 0 else 0,
                    'message': f"売上登録完了。売上：{total_sales:.0f}円、原価：{total_cost:.0f}円、粗利：{total_profit:.0f}円"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'sales_id': None,
                    'total_sales': 0,
                    'total_cost': 0,
                    'total_profit': 0,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def _generate_sales_id(cursor):
        """売上IDを採番"""
        cursor.execute("SELECT MAX(CAST(SUBSTR(sales_id, 3) AS INTEGER)) FROM sales_headers")
        row = cursor.fetchone()

        if row and row[0]:
            last_no = row[0]
            next_no = last_no + 1
        else:
            next_no = 1

        return f"SL-{next_no:06d}"

    @staticmethod
    def get_sales_details(sales_id):
        """
        売上明細を取得

        Args:
            sales_id: 売上ID

        Returns:
            list: 売上明細リスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM sales_details
                WHERE sales_id = ?
                ORDER BY id
            """, (sales_id,))

            return cur.fetchall()

    @staticmethod
    def get_sales_summary(start_date=None, end_date=None):
        """
        売上サマリーを取得

        Args:
            start_date: 開始日（オプション）
            end_date: 終了日（オプション）

        Returns:
            dict: 売上集計
        """
        with get_conn() as conn:
            cur = conn.cursor()

            query = """
                SELECT
                    COUNT(DISTINCT h.sales_id) as sales_count,
                    SUM(d.weight_kg) as total_weight,
                    SUM(d.sales_amount) as total_sales,
                    SUM(d.cost_amount) as total_cost,
                    SUM(d.profit) as total_profit
                FROM sales_headers h
                LEFT JOIN sales_details d ON h.sales_id = d.sales_id
                WHERE 1=1
            """

            params = []

            if start_date:
                query += " AND h.ship_date >= ?"
                params.append(str(start_date))

            if end_date:
                query += " AND h.ship_date <= ?"
                params.append(str(end_date))

            cur.execute(query, params)
            row = cur.fetchone()

            if row:
                sales_count, total_weight, total_sales, total_cost, total_profit = row
                total_sales = total_sales or 0
                total_cost = total_cost or 0
                total_profit = total_profit or 0

                return {
                    'sales_count': sales_count or 0,
                    'total_weight': total_weight or 0,
                    'total_sales': total_sales,
                    'total_cost': total_cost,
                    'total_profit': total_profit,
                    'profit_rate': (total_profit / total_sales * 100) if total_sales > 0 else 0,
                }
            else:
                return {
                    'sales_count': 0,
                    'total_weight': 0,
                    'total_sales': 0,
                    'total_cost': 0,
                    'total_profit': 0,
                    'profit_rate': 0,
                }
