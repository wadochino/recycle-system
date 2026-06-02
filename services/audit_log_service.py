"""
監査ログサービス
- 操作ログ記録
- 監査証跡の管理
- コンプライアンス対応
"""

from datetime import datetime
from db import get_conn

class AuditLogService:
    """監査ログを記録・管理するサービス"""

    @staticmethod
    def log_action(username, action, table_name="", record_id="", detail="", ip_address=""):
        """
        操作ログを記録

        Args:
            username: ユーザー名
            action: 操作内容（INSERT, UPDATE, DELETE, LOGIN等）
            table_name: テーブル名
            record_id: レコードID
            detail: 詳細情報
            ip_address: IPアドレス

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'log_id': int
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                cur.execute("""
                    INSERT INTO audit_logs (
                        timestamp,
                        username,
                        action,
                        table_name,
                        record_id,
                        detail,
                        ip_address,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    username,
                    action,
                    table_name,
                    record_id,
                    detail,
                    ip_address,
                    'success',
                ))

                log_id = cur.lastrowid
                conn.commit()

                return {
                    'success': True,
                    'message': f"操作ログを記録しました。",
                    'log_id': log_id
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}",
                    'log_id': None
                }

    @staticmethod
    def log_error(username, action, error_message, ip_address=""):
        """
        エラーログを記録

        Args:
            username: ユーザー名
            action: 操作内容
            error_message: エラーメッセージ
            ip_address: IPアドレス

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
                    INSERT INTO audit_logs (
                        timestamp,
                        username,
                        action,
                        detail,
                        ip_address,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    username,
                    action,
                    error_message,
                    ip_address,
                    'error',
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': "エラーログを記録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_audit_logs(username="", action="", table_name="", limit=100):
        """
        監査ログを検索

        Args:
            username: ユーザー名（フィルター）
            action: 操作内容（フィルター）
            table_name: テーブル名（フィルター）
            limit: 取得件数

        Returns:
            list: 監査ログのリスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            query = "SELECT * FROM audit_logs WHERE 1=1"
            params = []

            if username:
                query += " AND username = ?"
                params.append(username)

            if action:
                query += " AND action = ?"
                params.append(action)

            if table_name:
                query += " AND table_name = ?"
                params.append(table_name)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cur.execute(query, params)

            return cur.fetchall()

    @staticmethod
    def get_user_activity(username, days=30):
        """
        ユーザーのアクティビティを取得

        Args:
            username: ユーザー名
            days: 過去N日間

        Returns:
            list: アクティビティログのリスト
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM audit_logs
                WHERE username = ?
                  AND timestamp >= datetime('now', '-' || ? || ' days')
                ORDER BY timestamp DESC
            """, (username, days))

            return cur.fetchall()

    @staticmethod
    def get_action_summary(table_name="", days=30):
        """
        操作の集計を取得

        Args:
            table_name: テーブル名（オプション）
            days: 過去N日間

        Returns:
            list: {
                'action': str,
                'count': int,
                'last_timestamp': str
            }
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            if table_name:
                cur.execute("""
                    SELECT action, COUNT(*) as count, MAX(timestamp) as last_timestamp
                    FROM audit_logs
                    WHERE table_name = ?
                      AND timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY action
                    ORDER BY count DESC
                """, (table_name, days))
            else:
                cur.execute("""
                    SELECT action, COUNT(*) as count, MAX(timestamp) as last_timestamp
                    FROM audit_logs
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY action
                    ORDER BY count DESC
                """, (days,))

            return cur.fetchall()

    @staticmethod
    def get_error_count(days=7):
        """
        エラー件数を取得

        Args:
            days: 過去N日間

        Returns:
            int: エラー件数
        """
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT COUNT(*) FROM audit_logs
                WHERE status = 'error'
                  AND timestamp >= datetime('now', '-' || ? || ' days')
            """, (days,))

            result = cur.fetchone()
            return result[0] if result else 0
