"""
ID採番サービス
- 内部ID：ULID（Universally Unique Lexicographically Sortable Identifier）
- 表示用ID：FC-0001、KG-0001、LOT-0001 など

ULID の利点：
- UUID より短い（26文字）
- タイムスタンプを含む（ソート可能）
- 分散システムで安全（衝突の確率が極めて低い）
- 人間が読みやすい（Base32エンコーディング）

参考：
https://github.com/ulid/spec
"""

from ulid import ULID
import time
from db import get_conn

class InternalIDGenerator:
    """内部IDを生成する（ULID）"""

    @staticmethod
    def generate():
        """
        新しい ULID を生成

        Returns:
            str: ULID（例: 01ARZ3NDEKTSV4RRFFQ69G5FAV）
        """
        return str(ULID())

    @staticmethod
    def generate_with_timestamp(timestamp_ms=None):
        """
        指定されたタイムスタンプで ULID を生成

        Args:
            timestamp_ms: ミリ秒単位のタイムスタンプ（デフォルト: 現在時刻）

        Returns:
            str: ULID
        """
        if timestamp_ms is None:
            timestamp_ms = int(time.time() * 1000)
        return str(ULID(timestamp=timestamp_ms))


class DisplayIDGenerator:
    """表示用ID（現場向けコード）を採番する"""

    PREFIX_MAP = {
        "フレコン": "FC",
        "メッシュボックス": "MB",
        "カゴ": "KG",
        "パレット積み": "PL",
        "紙袋": "BG",
        "ロール": "RL",
        "その他": "OT",
    }

    @staticmethod
    def get_prefix(package):
        """荷姿からプレフィックスを取得"""
        return DisplayIDGenerator.PREFIX_MAP.get(package, "OT")

    @staticmethod
    def generate_inventory_id(package, offset=0):
        """
        在庫単位IDを採番（FC-0001形式）

        Args:
            package: 荷姿（フレコン、カゴなど）
            offset: オフセット（複数生成時に使用）

        Returns:
            str: 在庫単位ID（例: FC-0069）
        """
        prefix = DisplayIDGenerator.get_prefix(package)

        with get_conn() as conn:
            cur = conn.cursor()
            # 直接 MAX で最大値を取得（Python で番号部分を抽出）
            cur.execute("""
                SELECT unit_id
                FROM inventory
                WHERE unit_id LIKE ?
                ORDER BY unit_id DESC
                LIMIT 1
            """, (f"{prefix}-%",))

            row = cur.fetchone()

        if row is None:
            next_no = 1
        else:
            last_id = row[0]
            # 形式は "FC-0069" なので、最後の4文字を数字として取得
            try:
                last_no = int(last_id.split("-")[-1])
                next_no = last_no + 1
            except ValueError:
                next_no = 1

        next_no += offset
        return f"{prefix}-{next_no:04d}"

    @staticmethod
    def generate_receipt_id(offset=0):
        """
        受付IDを採番（R-0001形式）

        Args:
            offset: オフセット

        Returns:
            str: 受付ID（例: R-0027）
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(CAST(SUBSTR(receipt_id, 3) AS INTEGER)) FROM receipts")
            row = cur.fetchone()

        if row[0] is None:
            next_no = 1
        else:
            last_no = row[0]
            next_no = last_no + 1

        next_no += offset
        return f"R-{next_no:04d}"

    @staticmethod
    def generate_lot_id(offset=0):
        """
        加工ロットIDを採番（LOT-0001形式）

        Args:
            offset: オフセット

        Returns:
            str: ロットID（例: LOT-0003）
        """
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT MAX(CAST(SUBSTR(lot_id, 5) AS INTEGER)) FROM process_lots")
            row = cur.fetchone()

        if row[0] is None:
            next_no = 1
        else:
            last_no = row[0]
            next_no = last_no + 1

        next_no += offset
        return f"LOT-{next_no:04d}"
