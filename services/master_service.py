"""
マスタ管理サービス
- マスタ項目の追加
- マスタ項目の無効化
- 表示順の管理
"""

from db import (
    get_conn,
    insert_master_item,
    deactivate_master_item,
    update_master_sort_orders,
)

class MasterService:
    """マスタデータを管理するサービス"""

    @staticmethod
    def add_item(category, name):
        """
        マスタ項目を追加

        Args:
            category: カテゴリ（materials, colors など）
            name: 項目名

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
                    INSERT OR IGNORE INTO masters (
                        category,
                        name
                    )
                    VALUES (?, ?)
                """, (category, name))

                conn.commit()

                return {
                    'success': True,
                    'message': f"{name} を追加しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def deactivate_item(category, name):
        """
        マスタ項目を無効化

        Args:
            category: カテゴリ
            name: 項目名

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
                    UPDATE masters
                    SET is_active = 0
                    WHERE category = ?
                      AND name = ?
                """, (category, name))

                conn.commit()

                return {
                    'success': True,
                    'message': f"{name} を無効化しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def update_sort_orders(category, order_dict):
        """
        複数のマスタ項目の表示順を更新

        Args:
            category: カテゴリ
            order_dict: {項目名: 表示順} の辞書

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

                for name, sort_order in order_dict.items():
                    cur.execute("""
                        UPDATE masters
                        SET sort_order = ?
                        WHERE category = ?
                          AND name = ?
                    """, (int(sort_order), category, name))

                conn.commit()

                return {
                    'success': True,
                    'message': "表示順を保存しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }
