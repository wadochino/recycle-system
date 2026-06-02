#!/usr/bin/env python3
"""
Phase 5 テスト：QRコード、ユーザー認証、監査ログ
"""

import sys
import os
from db import init_db, migrate_phase5_add_columns
from services import QRCodeService, AuthService, AuditLogService

def test_auth_service():
    """ユーザー認証のテスト"""
    print("\n【ユーザー認証テスト】")

    # ユーザー作成
    result = AuthService.register_user(
        username="testuser",
        password="password123",
        full_name="テストユーザー",
        email="test@example.com"
    )
    print(f"✓ ユーザー作成：{result['message']}")

    # ユーザー認証成功
    user = AuthService.authenticate("testuser", "password123")
    assert user is not None, "認証に失敗"
    print(f"✓ ユーザー認証成功：{user['full_name']}")

    # ユーザー認証失敗
    user = AuthService.authenticate("testuser", "wrongpassword")
    assert user is None, "認証に失敗すべき"
    print("✓ 間違ったパスワードで拒否")

    # ロール割り当て
    result = AuthService.assign_role("testuser", "manager")
    assert result['success'], f"ロール割り当て失敗：{result['message']}"
    print(f"✓ ロール割り当て：{result['message']}")

    # ロール確認
    roles = AuthService.get_user_roles("testuser")
    assert "manager" in roles, "ロールが割り当てられていない"
    print(f"✓ ロール確認：{roles}")

    # 権限チェック
    has_perm = AuthService.has_permission("testuser", "manager")
    assert has_perm, "権限チェック失敗"
    print("✓ 権限チェック成功")

def test_qrcode_service():
    """QRコード管理のテスト"""
    print("\n【QRコード管理テスト】")

    # QRコード生成
    unit_id = "FC-0001"
    qrcode_data = QRCodeService.generate_qrcode(unit_id)
    assert qrcode_data, "QRコード生成失敗"
    print(f"✓ QRコード生成成功（データサイズ：{len(qrcode_data)}文字）")

    # QRコード情報保存
    result = QRCodeService.save_qrcode_map(
        unit_id=unit_id,
        qrcode_data=qrcode_data,
        qrcode_url="http://localhost:8501?unit_id=FC-0001"
    )
    assert result['success'], f"保存失敗：{result['message']}"
    print(f"✓ QRコード情報保存：{result['message']}")

    # QRコード情報取得
    qrcode_info = QRCodeService.get_qrcode(unit_id)
    assert qrcode_info is not None, "QRコード情報取得失敗"
    print(f"✓ QRコード情報取得：{unit_id}")

    # QRコード生成（URL）
    url_qrcode = QRCodeService.generate_qrcode_for_inventory_url(
        unit_id,
        base_url="http://localhost:8501"
    )
    assert url_qrcode, "URL QRコード生成失敗"
    print(f"✓ URL用QRコード生成成功")

    # HTML タグ取得
    html = QRCodeService.get_qrcode_html(unit_id, size="200px")
    assert "img" in html, "HTML生成失敗"
    print(f"✓ HTML img タグ生成成功")

def test_audit_log_service():
    """監査ログのテスト"""
    print("\n【監査ログテスト】")

    # 操作ログ記録
    result = AuditLogService.log_action(
        username="testuser",
        action="INSERT",
        table_name="inventory",
        record_id="FC-0001",
        detail="在庫を登録しました",
        ip_address="127.0.0.1"
    )
    assert result['success'], f"ログ記録失敗：{result['message']}"
    print(f"✓ 操作ログ記録：{result['message']}")

    # エラーログ記録
    result = AuditLogService.log_error(
        username="testuser",
        action="DELETE",
        error_message="削除に失敗しました",
        ip_address="127.0.0.1"
    )
    assert result['success'], f"エラーログ記録失敗：{result['message']}"
    print(f"✓ エラーログ記録：{result['message']}")

    # ログ検索
    logs = AuditLogService.get_audit_logs(
        username="testuser",
        limit=10
    )
    assert len(logs) > 0, "ログ検索失敗"
    print(f"✓ ログ検索成功：{len(logs)}件のログを取得")

    # ユーザーアクティビティ
    activity = AuditLogService.get_user_activity("testuser", days=30)
    assert len(activity) > 0, "アクティビティ取得失敗"
    print(f"✓ ユーザーアクティビティ取得：{len(activity)}件")

    # アクション統計
    summary = AuditLogService.get_action_summary(days=30)
    print(f"✓ アクション統計：{len(summary)}種類のアクション")

    # エラー件数
    error_count = AuditLogService.get_error_count(days=7)
    print(f"✓ エラー件数：{error_count}件")

def main():
    """テスト実行"""
    print("=" * 60)
    print("Phase 5 テスト：現場運用強化（QRコード・認証・監査ログ）")
    print("=" * 60)

    try:
        # DB初期化
        print("\n【DB初期化】")
        init_db()
        migrate_phase5_add_columns()
        print("✓ データベースを初期化しました")

        # テスト実行
        test_auth_service()
        test_qrcode_service()
        test_audit_log_service()

        print("\n" + "=" * 60)
        print("✅ すべてのテストが PASSED")
        print("=" * 60)

        print("\n【Phase 5 で追加される機能】")
        print("✓ ユーザー認証（パスワードハッシュ、ログイン・ログアウト）")
        print("✓ ロール管理（受取、検査、加工、出荷、管理、admin）")
        print("✓ QRコード管理（生成、保存、表示）")
        print("✓ 監査ログ（操作ログ、エラーログ、検索、統計）")

        return True

    except Exception as e:
        print(f"\n❌ エラー：{str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
