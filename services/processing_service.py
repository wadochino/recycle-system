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
        processing_weight=None,
        unprocessed_weight=None,
        updated_by=None,
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
                        SET status = ?, notes = ?
                        WHERE unit_id = ?
                    """, (
                        "加工済",
                        f"{process}へ投入 / 加工後ID:{','.join(new_ids)}",
                        src["在庫単位ID"]
                    ))

                    # 投入履歴を記録
                    cur.execute("""
                        INSERT INTO history (
                            unit_id,
                            operation,
                            details
                        )
                        VALUES (?, ?, ?)
                    """, (
                        src["在庫単位ID"],
                        "加工投入",
                        f"{process}へ投入 / 加工後ID:{','.join(new_ids)}"
                    ))

                # 4. 加工後在庫を作成
                output_weight = sum(output_weights)
                for i, w in enumerate(output_weights):
                    new_id = new_ids[i]
                    internal_id = InternalIDGenerator.generate()  # 内部ID（ULID）を生成

                    cur.execute("""
                        INSERT INTO inventory (
                            unit_id,
                            internal_id,
                            customer,
                            material,
                            color,
                            shape,
                            package,
                            weight_kg,
                            location,
                            status,
                            notes,
                            updated_by
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        new_id,
                        ",".join(source_ids),
                        source["取引先"],
                        source["樹脂"],
                        source["色"],
                        new_shape,
                        new_package,
                        int(w),
                        new_location,
                        new_status,
                        f"工程:{process} / 投入:{len(selected_rows)}件 / {note}",
                        updated_by
                    ))

                    # 加工完了履歴を記録
                    loss_weight = source_weight - output_weight
                    cur.execute("""
                        INSERT INTO history (
                            unit_id,
                            operation,
                            details
                        )
                        VALUES (?, ?, ?)
                    """, (
                        new_id,
                        "加工完了",
                        f"{process} / 投入:{len(selected_rows)}件 / ロス:{loss_weight}kg / {w}kg"
                    ))

                # 5. 加工ロットを作成
                lot_id = get_next_process_lot_id()
                loss_weight = source_weight - output_weight
                lot_internal_id = InternalIDGenerator.generate()  # 内部ID（ULID）を生成

                cur.execute("""
                    INSERT INTO process_lots (
                        lot_id,
                        process_date,
                        process,
                        input_ids,
                        output_ids,
                        input_weight,
                        output_weight,
                        loss_weight,
                        notes,
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

                # 未加工分の処理
                if unprocessed_weight and unprocessed_weight > 0:
                    # インデックスを加工後ユニット数の次の番号にして重複を避ける
                    unprocessed_id = get_next_unit_id(source["荷姿"], len(output_weights))
                    cur.execute("""
                        INSERT INTO inventory (
                            unit_id, internal_id, customer, material, color, shape,
                            package, weight_kg, location, status, notes, updated_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        unprocessed_id,
                        ",".join(source_ids),  # 親IDは投入在庫の unit_id リスト（加工後在庫と同じ）
                        source["取引先"],
                        source["樹脂"],
                        source["色"],
                        source["形状"],
                        source["荷姿"],
                        int(unprocessed_weight),
                        source["保管場所"],
                        source["状態"],
                        f"加工ロット{lot_id}から未加工分として自動作成",
                        updated_by
                    ))

                    # 未加工分の履歴記録
                    cur.execute("""
                        INSERT INTO history (
                            unit_id,
                            operation,
                            details
                        )
                        VALUES (?, ?, ?)
                    """, (
                        unprocessed_id,
                        "未加工在庫作成",
                        f"加工ロット{lot_id}の未加工分 {unprocessed_weight}kg"
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
