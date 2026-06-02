"""
原価配賦サービス
- 加工後在庫への原価配賦
- 重量按分による公平な配賦
- トランザクション管理
"""

from db import get_conn
from services import PriceService

class CostAllocationService:
    """加工品の原価配賦を管理するサービス"""

    @staticmethod
    def allocate_cost_by_weight(
        input_rows,
        output_weights,
        output_unit_ids,
        note="",
    ):
        """
        投入在庫の原価を、生成在庫に重量按分で配賦

        仕組み：
        1. 投入在庫の原価金額合計を算出
        2. 生成在庫の重量比率を算出
        3. 重量按分で各生成在庫へ配賦

        例：
        投入原価合計：20,000円
        生成A：600kg
        生成B：400kg
        生成合計：1,000kg

        配賦結果：
        生成A 原価：12,000円（20,000 × 600/1,000）
        生成B 原価：8,000円（20,000 × 400/1,000）

        Args:
            input_rows: 投入在庫リスト（辞書）
            output_weights: 生成重量リスト（整数）
            output_unit_ids: 生成在庫IDリスト（文字列）
            note: 備考

        Returns:
            dict: {
                'success': bool,
                'total_input_cost': float,
                'allocations': [
                    {'unit_id': str, 'cost': float, 'cost_price': float},
                    ...
                ],
                'message': str
            }
        """
        try:
            # 1. 投入原価合計を算出
            total_input_cost = 0.0

            for row in input_rows:
                # 各投入在庫の原価金額を取得
                cost = row.get('cost_amount', 0) or float(row.get('cost_amount', 0))
                total_input_cost += cost

            if total_input_cost == 0:
                # 原価がない場合（初期購入品など）
                return {
                    'success': True,
                    'total_input_cost': 0,
                    'allocations': [],
                    'message': "原価なし（初期購入品）"
                }

            # 2. 生成合計重量を算出
            total_output_weight = sum(output_weights)

            if total_output_weight == 0:
                return {
                    'success': False,
                    'total_input_cost': total_input_cost,
                    'allocations': [],
                    'message': "生成重量が0です"
                }

            # 3. 重量按分で配賦
            allocations = []

            for i, (weight, unit_id) in enumerate(zip(output_weights, output_unit_ids)):
                # 重量比率を算出
                weight_ratio = weight / total_output_weight

                # この在庫に配賦する原価
                allocated_cost = total_input_cost * weight_ratio

                # 原価単価を算出
                cost_unit_price = allocated_cost / weight if weight > 0 else 0

                allocations.append({
                    'unit_id': unit_id,
                    'weight': weight,
                    'weight_ratio': weight_ratio,
                    'cost': allocated_cost,
                    'cost_price': cost_unit_price,
                })

            return {
                'success': True,
                'total_input_cost': total_input_cost,
                'total_output_weight': total_output_weight,
                'allocations': allocations,
                'message': f"原価配賦完了：{total_input_cost:.0f}円を{len(allocations)}件に按分"
            }

        except Exception as e:
            return {
                'success': False,
                'total_input_cost': 0,
                'allocations': [],
                'message': f"エラー：{str(e)}"
            }

    @staticmethod
    def get_inventory_cost(unit_id):
        """
        在庫の原価情報を取得

        Args:
            unit_id: 在庫単位ID

        Returns:
            dict or None: 原価情報
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    unit_id,
                    item_code,
                    purchase_unit_price,
                    purchase_amount,
                    note
                FROM inventory_cost
                WHERE unit_id = ?
            """, (unit_id,))

            return cur.fetchone()

    @staticmethod
    def save_inventory_cost(unit_id, cost_amount, cost_unit_price, item_code=""):
        """
        在庫の原価情報を保存

        Args:
            unit_id: 在庫単位ID
            cost_amount: 原価金額
            cost_unit_price: 原価単価
            item_code: 品目コード

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

                # inventory テーブルの cost_amount と cost_unit_price を更新
                cur.execute("""
                    UPDATE inventory
                    SET cost_amount = ?, cost_unit_price = ?
                    WHERE unit_id = ?
                """, (
                    float(cost_amount),
                    float(cost_unit_price),
                    unit_id,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"原価情報を保存しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }
