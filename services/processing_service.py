"""
加工処理サービス
- 加工登録
- ロス計算
- 原価配賦（将来実装）
- トランザクション管理
- 内部ID（ULID）の生成・保存
"""

from datetime import datetime
from db import (
    get_conn,
    get_next_unit_id,
    get_next_process_lot_id,
    update_inventory_status,
    insert_inventory_row,
    insert_process_lot,
    insert_history,
)
from utils import InternalIDGenerator

class ProcessingService:
    """加工処理を管理するサービス"""

    @staticmethod
    def execute_processing(
        selected_rows,
        process,
        new_shape,
        new_package,
        new_location,
        new_status,
        output_weights,
        note="",
    ):
        """
        加工処理を実行（トランザクション管理）

        処理内容：
        1. 投入在庫情報を取得
        2. 加工後在庫IDを採番
        3. 投入在庫を加工済に更新
        4. 加工後在庫を作成
        5. 加工ロットを作成
        6. 履歴を記録

        Args:
            selected_rows: 投入在庫リスト（辞書のリスト）
            process: 工程名（粉砕、仕分けなど）
            new_shape: 加工後の形状
            new_package: 加工後の荷姿
            new_location: 加工後の保管場所
            new_status: 加工後の状態
            output_weights: 加工後の重量リスト（整数）
            note: 備考

        Returns:
            dict: {
                'success': bool,
                'lot_id': str,
                'new_ids': list[str],
                'message': str
            }
        """
        with get_conn() as conn:
            conn.isolation_level = None
            cur = conn.cursor()

            try:
                cur.execute("BEGIN IMMEDIATE")

                # 1. 投入情報の計算
                source_ids = [r["在庫単位ID"] for r in selected_rows]
                source = selected_rows[0]
                source_weight = sum(int(r["重量kg"]) for r in selected_rows)

                # 2. 加工後在庫IDを採番
                new_ids = []
                for i in range(len(output_weights)):
                    new_id = get_next_unit_id(new_package, i)
                    new_ids.append(new_id)

                # 3. 投入在庫を加工済に変更
                for src in selected_rows:
                    cur.execute("""
                        UPDATE inventory
                        SET status = ?, note = ?
                        WHERE unit_id = ?
                    """, (
                        "加工済",
                        f"{process}へ投入 / 加工後ID:{','.join(new_ids)}",
                        src["在庫単位ID"]
                    ))

                    # 投入履歴を記録
                    cur.execute("""
                        INSERT INTO inventory_history (
                            date,
                            unit_id,
                            action,
                            detail,
                            weight_kg
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        src["在庫単位ID"],
                        "加工投入",
                        f"{process}へ投入 / 加工後ID:{','.join(new_ids)}",
                        int(src["重量kg"])
                    ))

                # 4. 加工後在庫を作成
                output_weight = sum(output_weights)
                for i, w in enumerate(output_weights):
                    new_id = new_ids[i]
                    internal_id = InternalIDGenerator.generate()  # 内部ID（ULID）を生成

                    cur.execute("""
                        INSERT INTO inventory (
                            date,
                            customer,
                            material,
                            color,
                            shape,
                            package,
                            unit_id,
                            parent_id,
                            weight_kg,
                            location,
                            status,
                            note,
                            internal_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        source["取引先"],
                        source["樹脂"],
                        source["色"],
                        new_shape,
                        new_package,
                        new_id,
                        ",".join(source_ids),
                        int(w),
                        new_location,
                        new_status,
                        f"工程:{process} / 投入:{len(selected_rows)}件 / {note}",
                        internal_id  # 内部IDを保存
                    ))

                    # 加工完了履歴を記録
                    loss_weight = source_weight - output_weight
                    cur.execute("""
                        INSERT INTO inventory_history (
                            date,
                            unit_id,
                            action,
                            detail,
                            weight_kg
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        new_id,
                        "加工完了",
                        f"{process} / 投入:{len(selected_rows)}件 / ロス:{loss_weight}kg / {w}kg",
                        int(w)
                    ))

                # 5. 加工ロットを作成
                lot_id = get_next_process_lot_id()
                loss_weight = source_weight - output_weight
                lot_internal_id = InternalIDGenerator.generate()  # 内部ID（ULID）を生成

                cur.execute("""
                    INSERT INTO process_lots (
                        lot_id,
                        date,
                        process,
                        input_ids,
                        output_ids,
                        input_weight,
                        output_weight,
                        loss_weight,
                        note,
                        internal_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lot_id,
                    datetime.now().strftime("%Y-%m-%d"),
                    process,
                    ",".join(source_ids),
                    ",".join(new_ids),
                    source_weight,
                    output_weight,
                    loss_weight,
                    note,
                    lot_internal_id  # 内部IDを保存
                ))

                conn.commit()

                return {
                    'success': True,
                    'lot_id': lot_id,
                    'new_ids': new_ids,
                    'message': f"加工登録完了。ロットID：{lot_id}"
                }

            except Exception as e:
                conn.rollback()
                return {
                    'success': False,
                    'lot_id': None,
                    'new_ids': [],
                    'message': f"エラー：{str(e)}"
                }

    @staticmethod
    def calculate_loss(input_weight, output_weight):
        """ロス重量を計算"""
        return input_weight - output_weight

    @staticmethod
    def get_processing_patterns():
        """加工パターンを取得"""
        return [
            {
                'label': '仕分け → 製品在庫',
                'process': '仕分け',
                'default_shape': None,  # 元の形状を使用
                'default_status': '製品在庫',
            },
            {
                'label': '仕分け → 粉砕待ち',
                'process': '仕分け',
                'default_shape': None,
                'default_status': '粉砕待ち',
            },
            {
                'label': '粉砕 → 中間在庫',
                'process': '粉砕',
                'default_shape': '粉砕',
                'default_status': '中間在庫',
            },
            {
                'label': '粉砕 → 製品在庫',
                'process': '粉砕',
                'default_shape': '粉砕',
                'default_status': '製品在庫',
            },
            {
                'label': 'プレス → 製品在庫',
                'process': 'プレス',
                'default_shape': 'プレス品',
                'default_status': '製品在庫',
            },
            {
                'label': 'ペレット加工 → 製品在庫',
                'process': 'ペレット加工',
                'default_shape': 'ペレット',
                'default_status': '製品在庫',
            },
        ]
