"""
ユーザー認証・権限管理サービス
- ユーザー登録
- ログイン認証
- 権限管理
- パスワード管理
"""

import bcrypt
from datetime import datetime
from db import get_conn

class AuthService:
    """ユーザー認証と権限を管理するサービス"""

    @staticmethod
    def hash_password(password):
        """パスワードをハッシュ化"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    @staticmethod
    def verify_password(password, password_hash):
        """パスワードを検証"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def register_user(username, password, full_name, email=""):
        """
        ユーザーを登録

        Args:
            username: ユーザー名
            password: パスワード（プレーンテキスト）
            full_name: フルネーム
            email: メールアドレス

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

                password_hash = AuthService.hash_password(password)

                cur.execute("""
                    INSERT INTO users (
                        username,
                        password_hash,
                        full_name,
                        email,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    username,
                    password_hash,
                    full_name,
                    email,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"ユーザー '{username}' を登録しました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def authenticate(username, password):
        """
        ユーザーを認証

        Args:
            username: ユーザー名
            password: パスワード（プレーンテキスト）

        Returns:
            dict or None: ユーザー情報、認証失敗時は None
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM users
                WHERE username = ? AND is_active = 1
            """, (username,))

            user = cur.fetchone()

            if not user:
                return None

            if not AuthService.verify_password(password, user['password_hash']):
                return None

            return user

    @staticmethod
    def get_user_roles(username):
        """
        ユーザーのロールを取得

        Args:
            username: ユーザー名

        Returns:
            list: ロールリスト
        """
        with get_conn() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT role FROM user_roles
                WHERE username = ? AND is_active = 1
            """, (username,))

            roles = cur.fetchall()

            return [role[0] for role in roles]

    @staticmethod
    def assign_role(username, role):
        """
        ユーザーにロールを割り当て

        Args:
            username: ユーザー名
            role: ロール名

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
                    INSERT OR IGNORE INTO user_roles (username, role)
                    VALUES (?, ?)
                """, (username, role))

                conn.commit()

                return {
                    'success': True,
                    'message': f"ロール '{role}' をユーザー '{username}' に割り当てました。"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def has_permission(username, required_role):
        """
        ユーザーが権限を持っているか確認

        Args:
            username: ユーザー名
            required_role: 必要なロール

        Returns:
            bool: 権限がある場合 True
        """
        roles = AuthService.get_user_roles(username)
        return required_role in roles or "admin" in roles

    @staticmethod
    def change_password(username, old_password, new_password):
        """
        パスワードを変更

        Args:
            username: ユーザー名
            old_password: 現在のパスワード（プレーンテキスト）
            new_password: 新しいパスワード（プレーンテキスト）

        Returns:
            dict: {
                'success': bool,
                'message': str
            }
        """
        # 現在のパスワードを確認
        user = AuthService.authenticate(username, old_password)

        if not user:
            return {
                'success': False,
                'message': "現在のパスワードが正しくありません"
            }

        # 新しいパスワードをハッシュ化
        new_password_hash = AuthService.hash_password(new_password)

        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                cur.execute("""
                    UPDATE users
                    SET password_hash = ?, updated_at = ?
                    WHERE username = ?
                """, (
                    new_password_hash,
                    datetime.now().isoformat(),
                    username,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': "パスワードを変更しました"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def update_user_info(username, full_name=None, email=None):
        """
        ユーザー情報を更新

        Args:
            username: ユーザー名
            full_name: フルネーム（オプション）
            email: メールアドレス（オプション）

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

                updates = []
                params = []

                if full_name is not None:
                    updates.append("full_name = ?")
                    params.append(full_name)

                if email is not None:
                    updates.append("email = ?")
                    params.append(email)

                if not updates:
                    return {
                        'success': False,
                        'message': "更新する項目がありません"
                    }

                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(username)

                query = f"""
                    UPDATE users
                    SET {', '.join(updates)}
                    WHERE username = ?
                """

                cur.execute(query, params)
                conn.commit()

                return {
                    'success': True,
                    'message': "ユーザー情報を更新しました"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_user(username):
        """
        ユーザー情報を取得

        Args:
            username: ユーザー名

        Returns:
            dict or None: ユーザー情報
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT id, username, full_name, email, is_active, created_at, updated_at
                FROM users
                WHERE username = ?
            """, (username,))

            return cur.fetchone()
