"""
品目コード管理サービス
- 品目コードマスタの追加・管理
- 品目情報の検索
- トランザクション管理
"""

from db import get_conn

class ItemCodeService:
    """品目コードを管理するサービス"""

    @staticmethod
    def add_item_code(
        item_code,
        customer,
        internal_item_name1,
        internal_item_name2,
        customer_item_name,
        material,
        color,
        shape,
        package,
        note="",
    ):
        """
        品目コードを新規登録

        Args:
            item_code: 品目コード（例: ITEM-001）
            customer: 取引先（排出元）
            internal_item_name1: 社内品目名1
            internal_item_name2: 社内品目名2
            customer_item_name: 取引先向け品目名
            material: 樹脂
            color: 色
            shape: 形状
            package: 荷姿
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
                    INSERT INTO item_codes (
                        item_code,
                        customer,
                        internal_item_name1,
                        internal_item_name2,
                        customer_item_name,
                        material,
                        color,
                        shape,
                        package,
                        note
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item_code,
                    customer,
                    internal_item_name1,
                    internal_item_name2,
                    customer_item_name,
                    material,
                    color,
                    shape,
                    package,
                    note,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"品目コード {item_code} を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_item_code(item_code):
        """
        品目コードを検索

        Args:
            item_code: 品目コード

        Returns:
            dict or None: 品目情報、見つからない場合は None
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM item_codes
                WHERE item_code = ? AND is_active = 1
            """, (item_code,))

            return cur.fetchone()

    @staticmethod
    def get_all_item_codes():
        """
        すべての品目コードを取得（有効なもののみ）

        Returns:
            list: 品目コードリスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM item_codes
                WHERE is_active = 1
                ORDER BY item_code
            """)

            return cur.fetchall()

    @staticmethod
    def deactivate_item_code(item_code):
        """
        品目コードを無効化

        Args:
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

                cur.execute("""
                    UPDATE item_codes
                    SET is_active = 0
                    WHERE item_code = ?
                """, (item_code,))

                conn.commit()

                return {
                    'success': True,
                    'message': f"品目コード {item_code} を無効化しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }
