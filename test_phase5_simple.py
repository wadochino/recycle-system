#!/usr/bin/env python3
"""
Phase 5 シンプルテスト
"""

import sys
import os

print("=" * 60)
print("Phase 5 シンプルテスト")
print("=" * 60)

try:
    print("\n【DB初期化】")
    from db import init_db, migrate_phase5_add_columns
    init_db()
    migrate_phase5_add_columns()
    print("✓ データベースを初期化しました")

    print("\n【ユーザー認証テスト】")
    from services.auth_service import AuthService

    result = AuthService.register_user(
        username="testuser",
        password="password123",
        full_name="テストユーザー",
        email="test@example.com"
    )
    print(f"✓ ユーザー作成：{result['message']}")

    user = AuthService.authenticate("testuser", "password123")
    if user:
        print(f"✓ ユーザー認証成功：{user['full_name']}")
    else:
        print("❌ 認証失敗")

    print("\n【QRコード生成テスト】")
    from services.qrcode_service import QRCodeService

    qrcode_data = QRCodeService.generate_qrcode("FC-0001")
    print(f"✓ QRコード生成成功（{len(qrcode_data)}文字）")

    result = QRCodeService.save_qrcode_map("FC-0001", qrcode_data)
    print(f"✓ QRコード保存：{result['message']}")

    print("\n【監査ログテスト】")
    from services.audit_log_service import AuditLogService

    result = AuditLogService.log_action(
        username="testuser",
        action="INSERT",
        table_name="inventory",
        record_id="FC-0001",
        detail="テスト"
    )
    print(f"✓ 監査ログ記録：{result['message']}")

    logs = AuditLogService.get_audit_logs(username="testuser", limit=10)
    print(f"✓ ログ検索成功：{len(logs)}件")

    print("\n" + "=" * 60)
    print("✅ Phase 5 テスト PASSED")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ エラー：{str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
