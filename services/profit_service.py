"""
粗利管理サービス
- 粗利の計算
- 粗利率の計算
- 粗利集計・レポート
"""

from datetime import date
from db import get_conn

class ProfitService:
    """粗利を管理するサービス"""

    @staticmethod
    def calculate_profit(sales_amount, cost_amount):
        """
        粗利を計算

        粗利 = 売上金額 - 原価金額

        Args:
            sales_amount: 売上金額
            cost_amount: 原価金額

        Returns:
            float: 粗利
        """
        return float(sales_amount) - float(cost_amount)

    @staticmethod
    def calculate_profit_rate(profit, sales_amount):
        """
        粗利率を計算

        粗利率 (%) = (粗利 / 売上金額) × 100

        Args:
            profit: 粗利
            sales_amount: 売上金額

        Returns:
            float: 粗利率（パーセンテージ）
        """
        if sales_amount == 0:
            return 0.0

        return (float(profit) / float(sales_amount)) * 100

    @staticmethod
    def get_profit_by_destination(start_date=None, end_date=None):
        """
        販売先別粗利集計

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            list: 販売先別粗利
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            query = """
                SELECT
                    h.destination,
                    COUNT(DISTINCT h.sales_id) as sales_count,
                    SUM(d.weight_kg) as total_weight,
                    SUM(d.sales_amount) as total_sales,
                    SUM(d.cost_amount) as total_cost,
                    SUM(d.profit) as total_profit,
                    CASE
                        WHEN SUM(d.sales_amount) > 0
                        THEN (SUM(d.profit) / SUM(d.sales_amount)) * 100
                        ELSE 0
                    END as profit_rate
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

            query += " GROUP BY h.destination ORDER BY total_profit DESC"

            cur.execute(query, params)
            return cur.fetchall()

    @staticmethod
    def get_profit_by_item_code(start_date=None, end_date=None):
        """
        品目コード別粗利集計

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            list: 品目別粗利
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            query = """
                SELECT
                    d.item_code,
                    COUNT(DISTINCT h.sales_id) as sales_count,
                    SUM(d.weight_kg) as total_weight,
                    SUM(d.sales_amount) as total_sales,
                    SUM(d.cost_amount) as total_cost,
                    SUM(d.profit) as total_profit,
                    CASE
                        WHEN SUM(d.sales_amount) > 0
                        THEN (SUM(d.profit) / SUM(d.sales_amount)) * 100
                        ELSE 0
                    END as profit_rate
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

            query += " GROUP BY d.item_code ORDER BY total_profit DESC"

            cur.execute(query, params)
            return cur.fetchall()

    @staticmethod
    def get_profit_by_month(year=None, month=None):
        """
        月別粗利集計

        Args:
            year: 年（オプション）
            month: 月（オプション）

        Returns:
            list: 月別粗利
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            query = """
                SELECT
                    SUBSTR(h.ship_date, 1, 7) as year_month,
                    COUNT(DISTINCT h.sales_id) as sales_count,
                    SUM(d.weight_kg) as total_weight,
                    SUM(d.sales_amount) as total_sales,
                    SUM(d.cost_amount) as total_cost,
                    SUM(d.profit) as total_profit,
                    CASE
                        WHEN SUM(d.sales_amount) > 0
                        THEN (SUM(d.profit) / SUM(d.sales_amount)) * 100
                        ELSE 0
                    END as profit_rate
                FROM sales_headers h
                LEFT JOIN sales_details d ON h.sales_id = d.sales_id
                WHERE 1=1
            """

            params = []

            if year and month:
                year_month = f"{year}-{month:02d}"
                query += " AND SUBSTR(h.ship_date, 1, 7) = ?"
                params.append(year_month)
            elif year:
                query += " AND SUBSTR(h.ship_date, 1, 4) = ?"
                params.append(str(year))

            query += " GROUP BY SUBSTR(h.ship_date, 1, 7) ORDER BY year_month DESC"

            cur.execute(query, params)
            return cur.fetchall()

    @staticmethod
    def get_low_profit_items(threshold=10.0, start_date=None, end_date=None):
        """
        低粗利率の品目を取得

        Args:
            threshold: 粗利率の閾値（デフォルト：10%）
            start_date: 開始日
            end_date: 終了日

        Returns:
            list: 粗利率がしきい値未満の品目
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            query = """
                SELECT
                    d.item_code,
                    h.destination,
                    SUM(d.weight_kg) as total_weight,
                    SUM(d.sales_amount) as total_sales,
                    SUM(d.cost_amount) as total_cost,
                    SUM(d.profit) as total_profit,
                    CASE
                        WHEN SUM(d.sales_amount) > 0
                        THEN (SUM(d.profit) / SUM(d.sales_amount)) * 100
                        ELSE 0
                    END as profit_rate
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

            query += f""" GROUP BY d.item_code, h.destination
                HAVING profit_rate < ?
                ORDER BY profit_rate ASC
            """

            params.append(float(threshold))

            cur.execute(query, params)
            return cur.fetchall()
