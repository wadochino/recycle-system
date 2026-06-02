"""
拠点・保管場所管理サービス
- 拠点の登録・管理
- 保管場所の2階層管理
- トランザクション管理
"""

from db import get_conn

class SiteService:
    """拠点と保管場所を管理するサービス"""

    @staticmethod
    def add_site(site_code, site_name, address="", sort_order=999):
        """
        拠点を登録

        Args:
            site_code: 拠点コード（例: SITE-001）
            site_name: 拠点名
            address: 住所
            sort_order: 表示順

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
                    INSERT INTO sites (
                        site_code,
                        site_name,
                        address,
                        sort_order
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    site_code,
                    site_name,
                    address,
                    int(sort_order),
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"拠点 {site_name} を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_all_sites():
        """
        すべての拠点を取得（有効なもののみ）

        Returns:
            list: 拠点リスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM sites
                WHERE is_active = 1
                ORDER BY sort_order, id
            """)

            return cur.fetchall()

    @staticmethod
    def add_location(location_code, location_name, site_code, sort_order=999):
        """
        保管場所を登録（拠点に関連付け）

        Args:
            location_code: 保管場所コード（例: LOC-001）
            location_name: 保管場所名
            site_code: 所属拠点コード
            sort_order: 表示順

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
                    INSERT INTO locations_hierarchy (
                        location_code,
                        location_name,
                        site_code,
                        sort_order
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    location_code,
                    location_name,
                    site_code,
                    int(sort_order),
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"保管場所 {location_name} を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_locations_by_site(site_code):
        """
        指定した拠点の保管場所を取得

        Args:
            site_code: 拠点コード

        Returns:
            list: 保管場所リスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM locations_hierarchy
                WHERE site_code = ? AND is_active = 1
                ORDER BY sort_order, id
            """, (site_code,))

            return cur.fetchall()

    @staticmethod
    def get_all_locations_with_site():
        """
        すべての保管場所を拠点情報付きで取得

        Returns:
            list: 保管場所と拠点情報のリスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    l.location_code,
                    l.location_name,
                    s.site_code,
                    s.site_name,
                    l.sort_order
                FROM locations_hierarchy l
                LEFT JOIN sites s ON l.site_code = s.site_code
                WHERE l.is_active = 1
                ORDER BY s.sort_order, l.sort_order
            """)

            return cur.fetchall()
