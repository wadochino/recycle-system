"""
QRコード管理サービス
- QRコード生成
- QRコード情報の管理
- ラベル用QRコード作成
"""

import qrcode
from io import BytesIO
import base64
from db import get_conn

class QRCodeService:
    """QRコードを管理するサービス"""

    @staticmethod
    def generate_qrcode(data, version=1, box_size=10, border=2):
        """
        QRコードを生成

        Args:
            data: エンコードするデータ（文字列）
            version: QRコードバージョン（1-40）
            box_size: 各ボックスのサイズ
            border: 境界線のサイズ

        Returns:
            str: Base64エンコードされた画像データ
        """
        try:
            qr = qrcode.QRCode(
                version=version,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=box_size,
                border=border,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # BytesIOに画像を保存
            img_io = BytesIO()
            img.save(img_io, format='PNG')
            img_io.seek(0)

            # Base64エンコード
            img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

            return img_base64

        except Exception as e:
            raise Exception(f"QRコード生成エラー：{str(e)}")

    @staticmethod
    def save_qrcode_map(unit_id, qrcode_data, qrcode_url=""):
        """
        QRコード情報を保存

        Args:
            unit_id: 在庫単位ID
            qrcode_data: QRコードデータ（Base64）
            qrcode_url: QRコードURL（オプション）

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
                    INSERT OR REPLACE INTO qrcode_map (
                        unit_id,
                        qrcode_data,
                        qrcode_url,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, datetime('now'), datetime('now'))
                """, (
                    unit_id,
                    qrcode_data,
                    qrcode_url,
                ))

                conn.commit()

                return {
                    'success': True,
                    'message': f"QRコードを保存しました：{unit_id}"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def get_qrcode(unit_id):
        """
        QRコードを取得

        Args:
            unit_id: 在庫単位ID

        Returns:
            dict or None: QRコード情報
        """
        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("""
                SELECT * FROM qrcode_map
                WHERE unit_id = ?
            """, (unit_id,))

            return cur.fetchone()

    @staticmethod
    def generate_qrcode_for_inventory_url(unit_id, base_url=""):
        """
        在庫詳細ページのURLをQRコード化

        Args:
            unit_id: 在庫単位ID
            base_url: ベースURL（例：http://localhost:8501）

        Returns:
            str: Base64エンコードされたQRコード画像
        """
        # QRコード化するURL
        url = f"{base_url}?unit_id={unit_id}" if base_url else unit_id

        return QRCodeService.generate_qrcode(url)

    @staticmethod
    def get_qrcode_html(unit_id, size="200px"):
        """
        QRコードをHTML img タグで取得

        Args:
            unit_id: 在庫単位ID
            size: 画像サイズ

        Returns:
            str: HTML img タグ
        """
        qrcode_info = QRCodeService.get_qrcode(unit_id)

        if not qrcode_info or not qrcode_info['qrcode_data']:
            return ""

        qrcode_data = qrcode_info['qrcode_data']

        return f'''<img src="data:image/png;base64,{qrcode_data}"
                     width="{size}" height="{size}"
                     alt="QRCode: {unit_id}">'''
