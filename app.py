import base64
import urllib.parse
import streamlit as st
import csv
import os
import shutil
import unicodedata
import plotly.express as px
import plotly.graph_objects as go
from db import init_db, migrate_add_internal_ids, migrate_phase3_add_columns, migrate_phase4_add_columns, migrate_phase5_add_columns, migrate_add_updated_by, get_inventory_rows, insert_inventory_row, insert_receipt_row, get_pending_receipts, get_next_receipt_id, update_receipt_status, get_next_unit_id, update_inventory_status, update_inventory_location, update_inventory_row_fields, insert_history, get_history_rows, get_master_items, insert_master_item, get_master_items_with_order, update_master_sort_orders, deactivate_master_item, get_item_patterns, insert_item_pattern, get_next_process_lot_id, insert_process_lot, get_process_lots, get_shipped_inventory, get_inventory_summary
from services import ProcessingService, ReceiptService, ShippingService, InventoryService, MasterService, AuthService, AuditLogService
from datetime import date, datetime
from collections import defaultdict

# ページ設定
st.set_page_config(
    page_title="在庫管理システム",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# メニューのスタイルカスタマイズ
st.markdown("""
<style>
    div[role="radiogroup"] {
        font-size: 16px;
        line-height: 2.5;
    }
    div[role="radiogroup"] label {
        padding: 10px 15px;
        cursor: pointer;
    }
</style>
""", unsafe_allow_html=True)

def read_csv(file, fieldnames):
    if not os.path.exists(file):
        return []

    with open(file, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

headers = [
    "日付", "取引先", "樹脂", "色", "形状", "荷姿",
    "在庫単位ID", "親ID", "重量kg", "保管場所", "状態", "備考"
]

receipt_headers = [
    "受付ID", "日付", "取引先", "樹脂", "色", "形状",
    "荷姿", "予定数量", "保管場所", "状態"
]
move_log_headers = ["日付", "在庫単位ID", "移動前", "移動後", "備考"]

# DB初期化を最初に実行
init_db()
migrate_add_internal_ids()
migrate_phase3_add_columns()
migrate_phase4_add_columns()
migrate_phase5_add_columns()
migrate_add_updated_by()

materials = get_master_items("materials")
colors = get_master_items("colors")
shapes = get_master_items("shapes")
packages = get_master_items("packages")
locations = get_master_items("locations")

def make_new_id(rows, package):
    prefix_map = {
        "フレコン": "FC",
        "メッシュボックス": "MB",
        "カゴ": "KG",
        "パレット積み": "PL",
        "紙袋": "BG",
        "ロール": "RL",
        "その他": "OT",
    }
    prefix = prefix_map.get(package, "OT")
    return f"{prefix}-{len(rows) + 1:04d}"


def safe_int(value):
    try:
        # 💡 全角数字やスペースが含まれていても半角に正規化して処理するよう強化
        normalized = unicodedata.normalize("NFKC", str(value)).strip()
        return int(float(normalized))
    except:
        return 0

# 初期マスタ登録（キャッシュ済み）
@st.cache_resource
def init_default_masters():
    default_masters = {
        "materials": ["PP", "PE", "PET", "ABS", "HDPE", "その他"],
        "colors": ["N", "Z", "青", "黒", "グレー", "白", "透明", "その他"],
        "shapes": ["ランナー", "フィルム", "成形品", "粉砕", "ペレット", "ロール", "プレス品", "その他"],
        "packages": ["フレコン", "メッシュボックス", "カゴ", "パレット積み", "紙袋", "ロール", "その他"],
        "locations": ["第1工場", "第2工場", "倉庫", "出荷ヤード"],
    }
    for category, names in default_masters.items():
        for name in names:
            try:
                insert_master_item(category, name)
            except:
                pass  # 既に存在する場合はスキップ

init_default_masters()

materials = get_master_items("materials")
colors = get_master_items("colors")
shapes = get_master_items("shapes")
packages = get_master_items("packages")
locations = get_master_items("locations")

# ==========================
# Phase 5: ユーザー認証
# ==========================

import json
from pathlib import Path

# セッションファイル（ログイン状態を永続化）
SESSION_FILE = "session_state.json"

def load_session_state():
    """セッション状態をファイルから読み込む"""
    if Path(SESSION_FILE).exists():
        try:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    return None

def save_session_state(data):
    """セッション状態をファイルに保存"""
    try:
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

# セッション状態の初期化
if 'logged_in' not in st.session_state:
    # ファイルからセッション状態を復元
    saved_session = load_session_state()
    if saved_session:
        st.session_state.logged_in = saved_session.get('logged_in', False)
        st.session_state.username = saved_session.get('username', None)
        st.session_state.user_info = saved_session.get('user_info', None)
        st.session_state.selected_menu = saved_session.get('selected_menu', '予定登録')
    else:
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_info = None
        st.session_state.selected_menu = '予定登録'

# ログイン画面
if not st.session_state.logged_in:
    st.title("在庫管理システム - ログイン")

    st.subheader("ログイン")

    col1, col2 = st.columns(2)

    with col1:
        tab1, tab2 = st.tabs(["ログイン", "ユーザー作成"])

        with tab1:
            username = st.text_input("ユーザー名")
            password = st.text_input("パスワード", type="password")

            if st.button("ログイン"):
                user = AuthService.authenticate(username, password)

                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_info = user

                    # セッション状態をファイルに保存
                    save_session_state({
                        'logged_in': True,
                        'username': username,
                        'user_info': user,
                        'selected_menu': '予定登録'
                    })

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=username,
                        action="LOGIN",
                        detail="ユーザーがログインしました"
                    )

                    st.success(f"ログインしました：{user['full_name']}")
                    st.rerun()
                else:
                    st.error("ユーザー名またはパスワードが正しくありません")

                    # 失敗ログを記録
                    AuditLogService.log_error(
                        username=username,
                        action="LOGIN_FAILED",
                        error_message="ログイン失敗"
                    )

        with tab2:
            st.subheader("新規ユーザー作成")

            new_username = st.text_input("ユーザー名", key="new_user")
            new_password = st.text_input("パスワード", type="password", key="new_pass")
            new_password_confirm = st.text_input("パスワード再入力", type="password", key="new_pass_confirm")
            new_full_name = st.text_input("フルネーム")
            new_email = st.text_input("メールアドレス")

            if st.button("ユーザー作成"):
                if not new_username:
                    st.error("ユーザー名を入力してください")
                elif len(new_password) < 6:
                    st.error("パスワードは6文字以上です")
                elif new_password != new_password_confirm:
                    st.error("パスワードが一致しません")
                else:
                    result = AuthService.register_user(
                        new_username,
                        new_password,
                        new_full_name,
                        new_email
                    )

                    if result['success']:
                        st.success(result['message'])
                    else:
                        st.error(result['message'])

    st.stop()

# ログイン済みの場合、メインアプリケーション
st.title("在庫管理システム")

# ユーザー情報パネル
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    st.write(f"👤 {st.session_state.user_info['full_name']}")

with col3:
    if st.button("ログアウト"):
        # 監査ログを記録
        AuditLogService.log_action(
            username=st.session_state.username,
            action="LOGOUT",
            detail="ユーザーがログアウトしました"
        )

        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.user_info = None

        # セッションファイルを削除
        if Path(SESSION_FILE).exists():
            Path(SESSION_FILE).unlink()

        st.rerun()

menu_options = [
    "予定登録",
    "計量登録",
    "在庫一覧",
    "在庫編集",
    "加工登録",
    "出荷登録",
    "出荷実績",
    "在庫移動",
    "状態変更",
    "ラベル印刷",
    "パターン登録",
    "履歴一覧",
    "バックアップ",
    "マスタ管理",
    "加工ロット一覧",
    "QRコード生成",  # Phase 5
    "ユーザー管理",  # Phase 5
    "監査ログ",      # Phase 5
    "⚙️ ユーザー設定",  # Phase 5.1：ユーザー設定
]

# メニュー選択状態を復元
default_index = 0
if hasattr(st.session_state, 'selected_menu') and st.session_state.selected_menu in menu_options:
    default_index = menu_options.index(st.session_state.selected_menu)

menu = st.sidebar.radio(
    "📋 メニュー",
    menu_options,
    index=default_index
)

# 選択されたメニューをセッション状態とファイルに保存
if not hasattr(st.session_state, 'selected_menu') or menu != st.session_state.selected_menu:
    st.session_state.selected_menu = menu
    saved_session = load_session_state()
    if saved_session:
        saved_session['selected_menu'] = menu
        save_session_state(saved_session)
    else:
        save_session_state({
            'logged_in': st.session_state.logged_in,
            'username': st.session_state.username,
            'user_info': st.session_state.user_info,
            'selected_menu': menu
        })

# ==========================
# 予定登録
# ==========================
if menu == "予定登録":
    st.header("予定登録（前日入力）")

    receipt_date = st.date_input("日付", value=date.today())
    customer = st.text_input("取引先コード")

    material = st.selectbox("樹脂", materials)
    package = st.selectbox("荷姿", packages)

    planned_qty = st.number_input("予定数量", min_value=1, value=3)
    location = st.selectbox("保管予定場所", locations, key="receipt_location")

    if st.button("予定登録"):

        new_id = get_next_receipt_id()

        new_row = {
            "受付ID": new_id,
            "日付": str(receipt_date),
            "取引先": customer,
            "樹脂": material,
            "色": "",
            "形状": "",
            "荷姿": package,
            "予定数量": str(planned_qty),
            "保管場所": location,
            "状態": "予定",
        }

        insert_receipt_row(new_row)

        st.success(f"登録しました：{new_id}")

# ==========================
# 計量登録
# ==========================
elif menu == "計量登録":
    st.header("計量登録（現場用）")

    pending = get_pending_receipts()

    st.subheader("予定なしで登録")

    if st.checkbox("予定を使わず直接登録する"):
        customer = st.text_input("取引先コード（手入力）")
        material = st.selectbox("樹脂", materials, key="free_material")
        color = st.selectbox("色", colors, key="free_color")
        shape = st.selectbox("形状", shapes, key="free_shape")
        package = st.selectbox("荷姿", packages, key="free_package")
        location = st.text_input("保管場所")

        st.subheader("重量入力（改行で区切る）")

        weight_text = st.text_area(
            "重量を1行ずつ入力してください",
            placeholder="例:\n500\n800\n200",
            key="free_weight_text"
        )

        weights = []
        if weight_text:
            for line in weight_text.split("\n"):
                if line.strip():
                    w = safe_int(line)  # 💡 safe_int を通すことで全角数字の誤入力を救済
                    if w > 0:
                        weights.append(w)

        st.write(f"入力件数：{len(weights)}件 / 合計 {sum(weights)} kg")

        if st.button("計量登録（予定なし）"):
            if not customer:
                st.error("取引先コードを入力してください。")
            elif sum(weights) <= 0:
                st.error("重量を入力してください。")
            else:
                new_rows = []

                for w in weights:
                    new_id = get_next_unit_id(package, len(new_rows))

                    new_rows.append({
                        "日付": str(date.today()),
                        "取引先": customer,
                        "樹脂": material,
                        "色": color,
                        "形状": shape,
                        "荷姿": package,
                        "在庫単位ID": new_id,
                        "親ID": "",
                        "重量kg": str(w),
                        "保管場所": location,
                        "状態": "原料在庫",
                        "備考": "予定なし登録"
                    })

                for r in new_rows:
                    insert_inventory_row(r)

                    insert_history(
                        r["在庫単位ID"],
                        "計量登録",
                        f"{r['取引先']} / {r['樹脂']} / {r['重量kg']}kg"
                    )

                st.success(f"{len(new_rows)}件登録しました。")

    st.subheader("予定ありで登録")

    if not pending:
        st.warning("予定がありません")
    else:
        options = [
            f'{r["受付ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["荷姿"]} / {r["予定数量"]}個'
            for r in pending
        ]

        selected = st.selectbox("予定を選択", options)
        rec = pending[options.index(selected)]

        color = st.selectbox("色", colors, key="planned_color")
        shape = st.selectbox("形状", shapes, key="planned_shape")

        st.subheader("重量入力（改行で区切る）")

        weight_text = st.text_area(
            "重量を1行ずつ入力してください",
            placeholder="例:\n500\n800\n200",
            key="planned_weight_text"
        )

        weights = []
        if weight_text:
            for line in weight_text.split("\n"):
                if line.strip():
                    w = safe_int(line)  # 💡 safe_int を通すことで全角数字の誤入力を救済
                    if w > 0:
                        weights.append(w)

        st.write(f"入力件数：{len(weights)}件 / 合計 {sum(weights)} kg")

        if st.button("計量登録＋ラベル作成"):
            if sum(weights) <= 0:
                st.error("重量を入力してください。")
            else:
                new_rows = []

                for w in weights:
                    new_id = get_next_unit_id(rec["荷姿"], len(new_rows))

                    new_rows.append({
                        "日付": rec["日付"],
                        "取引先": rec["取引先"],
                        "樹脂": rec["樹脂"],
                        "色": color,
                        "形状": shape,
                        "荷姿": rec["荷姿"],
                        "在庫単位ID": new_id,
                        "親ID": rec["受付ID"],
                        "重量kg": str(w),
                        "保管場所": rec["保管場所"],
                        "状態": "原料在庫",
                        "備考": f"受付ID:{rec['受付ID']}"
                    })

                for r in new_rows:
                    insert_inventory_row(r)

                    insert_history(
                        r["在庫単位ID"],
                        "計量登録",
                        f"{r['取引先']} / {r['樹脂']} / {r['重量kg']}kg"
                    )

                update_receipt_status(rec["受付ID"], "計量済")

                st.success(f"{len(new_rows)}件登録しました。")
                st.info("印刷する場合は、左メニューの「ラベル印刷」から印刷してください。")

# ==========================
# 在庫一覧
# ==========================
elif menu == "在庫一覧":
    st.header("在庫一覧")

    rows = get_inventory_rows()
    active_rows = [
        r for r in rows
        if r["状態"] in ["原料在庫", "粉砕待ち", "中間在庫", "製品在庫"]
    ]

    if active_rows:
        customers = sorted(set(r["取引先"] for r in active_rows if r["取引先"]))
        locations_list = sorted(set(r["保管場所"] for r in active_rows if r["保管場所"]))
        statuses = sorted(set(r["状態"] for r in active_rows if r["状態"]))

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_customer = st.selectbox("取引先", ["すべて"] + customers)

        with col2:
            selected_location = st.selectbox("保管場所", ["すべて"] + locations_list)

        with col3:
            selected_status = st.selectbox("状態", ["すべて"] + statuses)

        filtered = active_rows

        if selected_customer != "すべて":
            filtered = [r for r in filtered if r["取引先"] == selected_customer]

        if selected_location != "すべて":
            filtered = [r for r in filtered if r["保管場所"] == selected_location]

        if selected_status != "すべて":
            filtered = [r for r in filtered if r["状態"] == selected_status]

        st.dataframe(filtered, use_container_width=True)

        total = sum(safe_int(r["重量kg"]) for r in filtered)
        st.subheader("表示中の集計")
        st.write(f"在庫単位数：{len(filtered)}")
        st.write(f"総重量：{total:,} kg")

        st.subheader("取引先ごとの合計重量")
        summary = defaultdict(int)
        for r in active_rows:
            summary[r["取引先"]] += safe_int(r["重量kg"])

        st.dataframe(
            [{"取引先": k, "合計重量kg": f"{v:,}"} for k, v in summary.items()],
            use_container_width=True
        )

        st.subheader("樹脂・色・形状ごとの合計重量")

        # フィルター
        col1, col2, col3 = st.columns(3)

        materials_list = sorted(set(r["樹脂"] for r in active_rows if r["樹脂"]))
        colors_list = sorted(set(r["色"] for r in active_rows if r["色"]))
        shapes_list = sorted(set(r["形状"] for r in active_rows if r["形状"]))

        with col1:
            selected_material = st.selectbox("樹脂", ["すべて"] + materials_list, key="summary_material")
        with col2:
            selected_color = st.selectbox("色", ["すべて"] + colors_list, key="summary_color")
        with col3:
            selected_shape = st.selectbox("形状", ["すべて"] + shapes_list, key="summary_shape")

        # 集計データを取得
        summary_data = get_inventory_summary()

        # フィルター適用
        if selected_material != "すべて":
            summary_data = [r for r in summary_data if r["樹脂"] == selected_material]
        if selected_color != "すべて":
            summary_data = [r for r in summary_data if r["色"] == selected_color]
        if selected_shape != "すべて":
            summary_data = [r for r in summary_data if r["形状"] == selected_shape]

        # 表示
        if summary_data:
            st.dataframe(summary_data, use_container_width=True)
        else:
            st.info("該当する在庫がありません。")

    else:
        st.write("現在庫がありません。")

# ==========================
# 在庫編集
# ==========================
elif menu == "在庫編集":
    st.header("在庫編集")

    rows = get_inventory_rows()

    if rows:
        # 編集対象を選択
        options = [f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]}' for r in rows]
        selected = st.selectbox("編集対象を選択", options)

        selected_idx = options.index(selected)
        target = rows[selected_idx]

        st.subheader("現在の情報")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"在庫単位ID：{target['在庫単位ID']}")
            st.write(f"取引先：{target['取引先']}")
            st.write(f"樹脂：{target['樹脂']}")
            st.write(f"色：{target['色']}")
            st.write(f"形状：{target['形状']}")
        with col2:
            st.write(f"荷姿：{target['荷姿']}")
            st.write(f"重量kg：{target['重量kg']}")
            st.write(f"保管場所：{target['保管場所']}")
            st.write(f"状態：{target['状態']}")
            st.write(f"備考：{target['備考']}")

        st.subheader("編集項目（変更したい項目だけ入力してください）")
        col1, col2 = st.columns(2)

        updates = {}

        with col1:
            new_customer = st.text_input("取引先", value=target['取引先'], key="edit_customer")
            if new_customer != target['取引先']:
                updates['取引先'] = new_customer

            new_material = st.selectbox("樹脂", materials, index=materials.index(target['樹脂']) if target['樹脂'] in materials else 0, key="edit_material")
            if new_material != target['樹脂']:
                updates['樹脂'] = new_material

            new_color = st.text_input("色", value=target['色'], key="edit_color")
            if new_color != target['色']:
                updates['色'] = new_color

            new_shape = st.text_input("形状", value=target['形状'], key="edit_shape")
            if new_shape != target['形状']:
                updates['形状'] = new_shape

        with col2:
            new_package = st.selectbox("荷姿", packages, index=packages.index(target['荷姿']) if target['荷姿'] in packages else 0, key="edit_package")
            if new_package != target['荷姿']:
                updates['荷姿'] = new_package

            new_weight = st.number_input("重量kg", value=float(target['重量kg']), key="edit_weight")
            if str(new_weight) != str(target['重量kg']):
                updates['重量kg'] = new_weight

            new_location = st.selectbox("保管場所", locations, index=locations.index(target['保管場所']) if target['保管場所'] in locations else 0, key="edit_location")
            if new_location != target['保管場所']:
                updates['保管場所'] = new_location

            new_notes = st.text_input("備考", value=target['備考'], key="edit_notes")
            if new_notes != target['備考']:
                updates['備考'] = new_notes

        if st.button("保存"):
            if updates:
                update_inventory_row_fields(target["在庫単位ID"], updates, st.session_state.username)

                # 更新内容を文字列化
                update_details = ", ".join([f"{k}: {target.get(k, '')} → {v}" for k, v in updates.items()])
                insert_history(
                    target["在庫単位ID"],
                    "在庫編集",
                    f"更新内容：{update_details}"
                )
                st.success("保存しました。")
                st.rerun()
            else:
                st.info("変更がありません。")
    else:
        st.write("在庫がありません。")

# ==========================
# 加工登録
# ==========================
elif menu == "加工登録":
    st.header("加工登録")

    rows = get_inventory_rows()

    from collections import Counter

    status_counter = Counter([r["状態"] for r in rows])
    status_text = " | ".join([f"{s}({c})" for s, c in sorted(status_counter.items())])
    st.markdown(f"**全在庫：{len(rows)}件**  \n{status_text}")

    active_rows = [r for r in rows if r["状態"] not in ["加工済", "出荷済"]]

    if not active_rows:
        st.warning("加工できる在庫がありません。")
    else:
        st.subheader("加工対象の検索・フィルター")

        # フィルター条件
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            filter_customer = st.selectbox(
                "取引先",
                ["すべて"] + sorted(set(r["取引先"] for r in active_rows if r["取引先"])),
                key="filter_customer_processing"
            )

        with col2:
            filter_material = st.selectbox(
                "樹脂",
                ["すべて"] + sorted(set(r["樹脂"] for r in active_rows if r["樹脂"])),
                key="filter_material_processing"
            )

        with col3:
            filter_status = st.selectbox(
                "状態",
                ["すべて"] + sorted(set(r["状態"] for r in active_rows if r["状態"])),
                key="filter_status_processing"
            )

        with col4:
            # 入荷日でフィルター（最古の日付から今日まで）
            filter_date_from = st.date_input(
                "入荷日（以降）",
                value=None,
                key="filter_date_processing"
            )

        # フィルター適用
        filtered_rows = active_rows
        if filter_customer != "すべて":
            filtered_rows = [r for r in filtered_rows if r["取引先"] == filter_customer]
        if filter_material != "すべて":
            filtered_rows = [r for r in filtered_rows if r["樹脂"] == filter_material]
        if filter_status != "すべて":
            filtered_rows = [r for r in filtered_rows if r["状態"] == filter_status]
        if filter_date_from:
            filtered_rows = [r for r in filtered_rows if r["日付"] >= str(filter_date_from)]

        st.info(f"フィルター結果：{len(filtered_rows)}件 / 全体：{len(active_rows)}件")

        options = [
            f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["形状"]} / {r["重量kg"]}kg / {r["状態"]} / {r["日付"]}'
            for r in filtered_rows
        ]

        selected_items = st.multiselect("加工対象を選択", options)

        selected_rows = []
        for item in selected_items:
            selected_rows.append(filtered_rows[options.index(item)])

        if not selected_rows:
            st.warning("加工する在庫を選択してください。")
            st.stop()

        source = selected_rows[0]
        source_ids = [r["在庫単位ID"] for r in selected_rows]
        source_weight = sum(safe_int(r["重量kg"]) for r in selected_rows)

        st.subheader("加工前情報")

        source_table = [
            {"項目": "在庫ID", "内容": source["在庫単位ID"]},
            {"項目": "取引先", "内容": source["取引先"]},
            {"項目": "樹脂", "内容": source["樹脂"]},
            {"項目": "色", "内容": source["色"]},
            {"項目": "形状", "内容": source["形状"]},
            {"項目": "荷姿", "内容": source["荷姿"]},
            {"項目": "重量kg", "内容": source["重量kg"]},
            {"項目": "保管場所", "内容": source["保管場所"]},
            {"項目": "状態", "内容": source["状態"]},
        ]

        st.write(f"投入数：{len(selected_rows)}件")
        st.write(f"投入合計重量：{source_weight:,} kg")
        st.dataframe(selected_rows, use_container_width=True)

        st.table(source_table)

        st.subheader("加工パターン")

        pattern = st.selectbox(
            "加工パターンを選択",
            [
                "手動で選ぶ",
                "仕分け → 製品在庫",
                "仕分け → 粉砕待ち",
                "粉砕 → 中間在庫",
                "粉砕 → 製品在庫",
                "プレス → 製品在庫",
                "ペレット加工 → 製品在庫",
            ]
        )

        process = "その他"
        default_shape = shapes[0]
        default_status = "中間在庫"

        if pattern == "仕分け → 製品在庫":
            process = "仕分け"
            default_shape = source["形状"]
            default_status = "製品在庫"

        elif pattern == "仕分け → 粉砕待ち":
            process = "仕分け"
            default_shape = source["形状"]
            default_status = "粉砕待ち"

        elif pattern == "粉砕 → 中間在庫":
            process = "粉砕"
            default_shape = "粉砕"
            default_status = "中間在庫"

        elif pattern == "粉砕 → 製品在庫":
            process = "粉砕"
            default_shape = "粉砕"
            default_status = "製品在庫"

        elif pattern == "プレス → 製品在庫":
            process = "プレス"
            default_shape = "プレス品"
            default_status = "製品在庫"

        elif pattern == "ペレット加工 → 製品在庫":
            process = "ペレット加工"
            default_shape = "ペレット"
            default_status = "製品在庫"

        if pattern == "手動で選ぶ":
            process = st.selectbox("工程", ["仕分け", "破砕", "粉砕", "プレス", "ペレット加工", "その他"])
        else:
            st.write(f"工程：{process}")

        new_shape = st.selectbox(
            "加工後の形状",
            shapes,
            index=shapes.index(default_shape) if default_shape in shapes else 0
        )

        new_package = st.selectbox("加工後の荷姿", packages)

        new_location = st.text_input("加工後の保管場所", value=source["保管場所"])

        new_status = st.selectbox(
            "加工後の状態",
            ["粉砕待ち", "中間在庫", "製品在庫"],
            index=["粉砕待ち", "中間在庫", "製品在庫"].index(default_status)
        )

        st.subheader("加工後重量入力（改行で区切る）")

        output_text = st.text_area(
            "加工後重量を1行ずつ入力してください",
            placeholder="例:\n500\n700\n600",
            key="process_output_text"
        )

        output_weights = []

        if output_text:
            for line in output_text.split("\n"):
                if line.strip():
                    w = safe_int(line)  # 💡 ここでも全角数字を許容
                    if w > 0:
                        output_weights.append(w)

        output_weight = sum(output_weights)

        st.write(f"加工後個数：{len(output_weights)}件 / 合計 {output_weight:,} kg")

        source_weight = sum(safe_int(r["重量kg"]) for r in selected_rows)

        # **新機能：加工対象合計重量を入力（デフォルト：投入全体）
        st.subheader("加工対象情報")
        processing_weight = st.number_input(
            "加工対象合計重量（kg）",
            value=source_weight,
            min_value=0,
            max_value=source_weight,
            help="投入在庫の中で、実際に加工した重量を入力してください。残りは『未加工在庫』として自動作成されます。"
        )

        unprocessed_weight = source_weight - processing_weight
        loss_weight = processing_weight - output_weight

        st.info(f"投入合計：{source_weight:,} kg")
        st.info(f"加工対象：{processing_weight:,} kg")
        st.info(f"加工結果：{output_weight:,} kg")
        st.info(f"ロス：{loss_weight:,} kg")
        if unprocessed_weight > 0:
            st.warning(f"未加工（明日以降に加工）：{unprocessed_weight:,} kg ← 新しい受入在庫として自動作成されます")

        note = st.text_area("備考")

        if st.button("加工登録"):
            if output_weight <= 0:
                st.error("加工後重量を入力してください。")
            elif loss_weight < 0:
                st.error("加工後重量が加工対象重量を超えています。")
            else:
                # ProcessingService を使用してトランザクション管理
                result = ProcessingService.execute_processing(
                    selected_rows=selected_rows,
                    process=process,
                    new_shape=new_shape,
                    new_package=new_package,
                    new_location=new_location,
                    new_status=new_status,
                    output_weights=output_weights,
                    note=note,
                    processing_weight=processing_weight,  # 加工対象重量を追加
                    unprocessed_weight=unprocessed_weight,  # 未加工重量を追加
                )

                if result['success']:
                    st.success(f"加工登録完了。ロットID：{result['lot_id']} / 新ID：{', '.join(result['new_ids'])}")
                    if unprocessed_weight > 0:
                        st.info(f"未加工在庫 {unprocessed_weight:,}kg を新しい受入在庫として自動作成しました")
                else:
                    st.error(result['message'])

# ==========================
# 出荷登録
# ==========================
elif menu == "出荷登録":
    st.header("出荷登録")

    rows = get_inventory_rows()
    shippable_rows = [r for r in rows if r["状態"] == "製品在庫"]

    if not shippable_rows:
        st.warning("出荷できる製品在庫がありません。")
    else:
        options = [
            f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["形状"]} / {r["重量kg"]}kg / {r["保管場所"]}'
            for r in shippable_rows
        ]

        selected_items = st.multiselect("出荷する在庫を選択", options)

        col1, col2 = st.columns(2)

        with col1:
            ship_date = st.date_input("出荷日", value=date.today())

        with col2:
            destination = st.text_input("出荷先")

        col3, col4 = st.columns(2)

        with col3:
            ship_method = st.selectbox(
                "出荷手段",
                ["コンテナ", "大型車", "その他"]
            )

        with col4:
            st.write("")  # スペーサー

        note = st.text_area("備考")

        selected_ids = []
        total_weight = 0

        for item in selected_items:
            r = shippable_rows[options.index(item)]
            selected_ids.append(r["在庫単位ID"])
            total_weight += safe_int(r["重量kg"])

        st.info(f"出荷対象：{len(selected_ids)}件 / 合計 {total_weight:,} kg")

        if st.button("出荷登録"):
            if not selected_ids:
                st.error("出荷する在庫を選択してください。")
            elif not destination:
                st.error("出荷先を入力してください。")
            elif not ship_method:
                st.error("出荷手段を選択してください。")
            else:
                # ShippingService を使用してトランザクション管理
                result = ShippingService.register_shipping(
                    selected_ids=selected_ids,
                    ship_date=ship_date,
                    destination=destination,
                    note=f"{ship_method} / {note}" if note else ship_method,
                )

                if result['success']:
                    st.success(f"{result['count']}件を出荷登録しました。合計 {total_weight:,} kg")
                else:
                    st.error(result['message'])

# ==========================
# 出荷実績
# ==========================
elif menu == "出荷実績":
    # ヘッダー装飾（控えめな色付け）
    st.markdown("""
        <div style='text-align: center; padding: 20px; background: #f0f7f4; border-left: 5px solid #2d5016; border-radius: 8px; margin-bottom: 20px;'>
            <h1 style='color: #1f77b4; font-size: 2.5em; margin: 0;'>出荷実績ダッシュボード</h1>
            <p style='color: #666; font-size: 1em; margin-top: 5px;'>リアルタイム出荷状況の監視・分析</p>
        </div>
    """, unsafe_allow_html=True)

    shipped_data = get_shipped_inventory()

    if not shipped_data:
        st.info("出荷実績がありません。")
    else:
        # 出荷日を抽出（備考から「出荷日:XXXX」を取得）
        def extract_ship_date(notes):
            if notes and "出荷日:" in notes:
                parts = notes.split(" / ")
                for part in parts:
                    if part.startswith("出荷日:"):
                        return part.replace("出荷日:", "")
            return ""

        # 出荷先を抽出（備考から「出荷先:XXX」を取得）
        def extract_destination(notes):
            if notes and "出荷先:" in notes:
                parts = notes.split(" / ")
                for part in parts:
                    if part.startswith("出荷先:"):
                        return part.replace("出荷先:", "")
            return ""

        # 出荷手段を抽出（備考から「コンテナ」「大型車」などを取得）
        def extract_ship_method(notes):
            if notes:
                parts = notes.split(" / ")
                for part in parts:
                    if not part.startswith("出荷日:") and not part.startswith("出荷先:"):
                        return part.strip()
            return ""

        # フィルター用の出荷先リストを生成
        destinations = sorted(set(
            extract_destination(r["備考"])
            for r in shipped_data
            if extract_destination(r["備考"])
        ))

        # フィルターセクション（expanderで畳める）
        with st.expander("フィルター設定", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                filter_customer_ship = st.selectbox(
                    "取引先",
                    ["すべて"] + sorted(set(r["取引先"] for r in shipped_data if r["取引先"])),
                    key="filter_customer_ship"
                )

            with col2:
                filter_material_ship = st.selectbox(
                    "樹脂",
                    ["すべて"] + sorted(set(r["樹脂"] for r in shipped_data if r["樹脂"])),
                    key="filter_material_ship"
                )

            with col3:
                filter_destination_ship = st.selectbox(
                    "出荷先",
                    ["すべて"] + destinations,
                    key="filter_destination_ship"
                )

            with col4:
                col4a, col4b = st.columns(2)
                with col4a:
                    filter_ship_date_from = st.date_input(
                        "開始日",
                        value=None,
                        key="filter_ship_date_from"
                    )
                with col4b:
                    filter_ship_date_to = st.date_input(
                        "終了日",
                        value=None,
                        key="filter_ship_date_to"
                    )

        # フィルター適用
        filtered_ship = shipped_data
        if filter_customer_ship != "すべて":
            filtered_ship = [r for r in filtered_ship if r["取引先"] == filter_customer_ship]
        if filter_material_ship != "すべて":
            filtered_ship = [r for r in filtered_ship if r["樹脂"] == filter_material_ship]
        if filter_destination_ship != "すべて":
            filtered_ship = [r for r in filtered_ship if extract_destination(r["備考"]) == filter_destination_ship]
        if filter_ship_date_from:
            filtered_ship = [r for r in filtered_ship if extract_ship_date(r["備考"]) >= str(filter_ship_date_from)]
        if filter_ship_date_to:
            filtered_ship = [r for r in filtered_ship if extract_ship_date(r["備考"]) <= str(filter_ship_date_to)]

        # 全体集計情報
        total_weight = sum(safe_int(r["重量kg"]) for r in filtered_ship)
        customer_summary = defaultdict(float)
        for r in filtered_ship:
            customer_summary[r["取引先"]] += safe_int(r["重量kg"])

        # 集計サマリー表示（シンプルタイプ + 控えめな色付け）
        st.markdown("""
            <div style='background: #f0f7f4; padding: 15px; border-radius: 8px; margin: 10px 0;'>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("出荷件数", f"{len(filtered_ship):,}")
        with col2:
            st.metric("合計重量", f"{total_weight:,.0f} kg")
        with col3:
            st.metric("取引先数", len(customer_summary))
        with col4:
            # 出荷ロット数を計算
            lot_summary_temp = defaultdict(lambda: {"件数": 0, "合計重量kg": 0})
            for r in filtered_ship:
                ship_date = extract_ship_date(r["備考"])
                destination = extract_destination(r["備考"])
                ship_method = extract_ship_method(r["備考"])
                lot_key = (r["取引先"], ship_date, destination, ship_method)
                lot_summary_temp[lot_key]["件数"] += 1
            st.metric("出荷ロット数", len(lot_summary_temp))

        st.markdown("</div>", unsafe_allow_html=True)

        # 出荷ロット別集計（取引先 + 出荷日 + 出荷先 + 出荷手段）
        lot_summary = defaultdict(lambda: {"件数": 0, "合計重量kg": 0})
        for r in filtered_ship:
            ship_date = extract_ship_date(r["備考"])
            destination = extract_destination(r["備考"])
            ship_method = extract_ship_method(r["備考"])
            lot_key = (r["取引先"], ship_date, destination, ship_method)
            lot_summary[lot_key]["件数"] += 1
            lot_summary[lot_key]["合計重量kg"] += safe_int(r["重量kg"])

        lot_data = []
        for (customer, ship_date, destination, ship_method), summary in sorted(lot_summary.items()):
            lot_data.append({
                "取引先": customer,
                "出荷日": ship_date,
                "出荷先": destination,
                "出荷手段": ship_method,
                "件数": summary["件数"],
                "合計重量kg": f"{summary['合計重量kg']:,.0f}"
            })

        # タブで構成
        if lot_data:
            st.markdown("---")
            st.markdown("### 出荷ロット詳細")
            tab1, tab2, tab3 = st.tabs(["ロット一覧", "ロット詳細", "詳細テーブル"])

            # Tab 1: ロット一覧
            with tab1:
                st.markdown("#### ロット一覧")
                st.dataframe(lot_data, use_container_width=True, height=450)

            # Tab 2: ロット詳細
            with tab2:
                st.markdown("#### ロット詳細")
                lot_options = [f"{d['取引先']} - {d['出荷日']} - {d['出荷先']} - {d['出荷手段']} ({d['件数']}件 / {d['合計重量kg']}kg)" for d in lot_data]
                selected_lot_display = st.selectbox("ロットを選択", lot_options, key="lot_select")

                if selected_lot_display:
                    # 選択されたロットのインデックスを取得
                    selected_lot_idx = lot_options.index(selected_lot_display)
                    selected_lot = lot_data[selected_lot_idx]

                    # そのロットに該当するデータをフィルタリング
                    lot_detail = [r for r in filtered_ship
                                  if (r["取引先"] == selected_lot["取引先"] and
                                      extract_ship_date(r["備考"]) == selected_lot["出荷日"] and
                                      extract_destination(r["備考"]) == selected_lot["出荷先"] and
                                      extract_ship_method(r["備考"]) == selected_lot["出荷手段"])]

                    # ロット詳細情報
                    st.info(f"✓ {selected_lot_display}")

                    # ロット内統計
                    lot_total_weight = sum(safe_int(r["重量kg"]) for r in lot_detail)
                    lot_material_summary = defaultdict(float)
                    for r in lot_detail:
                        lot_material_summary[r["樹脂"]] += safe_int(r["重量kg"])

                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    with stat_col1:
                        st.metric("品目数", len(lot_detail))
                    with stat_col2:
                        st.metric("合計重量", f"{lot_total_weight:,.0f} kg")
                    with stat_col3:
                        st.metric("樹脂種類", len(lot_material_summary))

                    # ロット内の詳細履歴
                    st.markdown("#### 詳細履歴")
                    detail_columns = ["在庫単位ID", "取引先", "樹脂", "荷姿", "重量kg", "備考", "更新日時"]
                    detail_data = [[r.get(col, "") for col in detail_columns] for r in lot_detail]

                    st.dataframe(
                        {col: [row[i] for row in detail_data] for i, col in enumerate(detail_columns)},
                        use_container_width=True,
                        height=350
                    )

                    # ロット内の樹脂別内訳
                    if lot_material_summary:
                        st.markdown("#### 樹脂別内訳")
                        lot_material_data = [{"樹脂": k, "合計重量kg": f"{v:,.0f}"} for k, v in sorted(lot_material_summary.items(), key=lambda x: x[1], reverse=True)]
                        st.dataframe(lot_material_data, use_container_width=True)

            # Tab 3: 詳細テーブル
            with tab3:
                st.markdown("#### 全出荷履歴")
                detail_columns = ["在庫単位ID", "取引先", "樹脂", "荷姿", "重量kg", "備考", "更新日時"]
                detail_data = [[r.get(col, "") for col in detail_columns] for r in filtered_ship]

                st.dataframe(
                    {col: [row[i] for row in detail_data] for i, col in enumerate(detail_columns)},
                    use_container_width=True,
                    height=500
                )

        else:
            st.info("該当する出荷ロットがありません。")

        st.markdown("---")
        st.markdown("""
            <div style='text-align: center; padding: 15px; background: #f0f2f6; border-radius: 8px;'>
                <p style='margin: 0; color: #666;'>将来の機能 — 単価を入力すれば売上計算・粗利分析も可能になります</p>
            </div>
        """, unsafe_allow_html=True)

# ==========================
# パターン登録
# ==========================
elif menu == "パターン登録":
    st.header("パターン登録")

    customer = st.text_input("取引先コード")

    material = st.selectbox("樹脂", materials)
    color = st.selectbox("色", colors)
    shape = st.selectbox("形状", shapes)
    package = st.selectbox("荷姿", packages)

    if st.button("パターン保存"):
        if not customer:
            st.error("取引先コードを入力してください。")
        else:
            insert_item_pattern({
                "取引先": customer,
                "樹脂": material,
                "色": color,
                "形状": shape,
                "荷姿": package
            })
            st.success("パターン登録しました。")

    st.subheader("登録済みパターン")
    patterns = get_item_patterns()

    if patterns:
        st.dataframe(patterns, use_container_width=True)
    else:
        st.write("まだパターンがありません。")

# ==========================
# 在庫移動
# ==========================
elif menu == "在庫移動":
    st.header("在庫移動（一括移動）")

    rows = get_inventory_rows()
    active_rows = [r for r in rows if r["状態"] not in ["加工済", "出荷済", "誤登録", "廃棄", "返品"]]

    if not active_rows:
        st.warning("移動できる在庫がありません。")
    else:
        dates = sorted(set(r["日付"] for r in active_rows if r["日付"]))
        customers = sorted(set(r["取引先"] for r in active_rows if r["取引先"]))

        col1, col2 = st.columns(2)

        with col1:
            selected_date = st.selectbox("入荷日で絞り込み", ["すべて"] + dates)

        with col2:
            selected_customer = st.selectbox("取引先で絞り込み", ["すべて"] + customers)

        filtered = active_rows

        if selected_date != "すべて":
            filtered = [r for r in filtered if r["日付"] == selected_date]

        if selected_customer != "すべて":
            filtered = [r for r in filtered if r["取引先"] == selected_customer]

        st.subheader("移動対象候補")
        st.write(f"候補件数：{len(filtered)}件")

        if filtered:
            st.dataframe(filtered, use_container_width=True)

            options = [
                f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["形状"]} / {r["重量kg"]}kg / {r["保管場所"]}'
                for r in filtered
            ]

            selected_items = st.multiselect("移動する在庫を選択", options)

            selected_ids = []
            total_weight = 0

            for item in selected_items:
                r = filtered[options.index(item)]
                selected_ids.append(r["在庫単位ID"])
                total_weight += safe_int(r["重量kg"])

            st.info(f"選択中：{len(selected_ids)}件 / 合計 {total_weight:,} kg")

            locations_list = [
                "出荷ヤード",
                "第2工場",
                "富士事業所",
                "入山瀬倉庫",
                "依田橋倉庫"
            ]

            new_location = st.selectbox("移動先", locations_list)
            note = st.text_input("備考（任意）")

            if st.button("一括移動実行"):
                if not selected_ids:
                    st.error("移動する在庫を選択してください。")
                else:
                    for r in rows:
                        if r["在庫単位ID"] in selected_ids:
                            old_location = r["保管場所"]

                            update_inventory_location(
                                r["在庫単位ID"],
                                new_location,
                                st.session_state.username
                            )

                            insert_history(
                                r["在庫単位ID"],
                                "在庫移動",
                                f"{old_location} → {new_location} / {note}"
                            )

                    st.success(f"{len(selected_ids)}件を {new_location} に移動しました。")

# ==========================
# 状態変更
# ==========================
elif menu == "状態変更":
    st.header("状態変更")

    rows = get_inventory_rows()

    target_rows = [r for r in rows if r["状態"] not in ["加工済", "出荷済", "誤登録", "廃棄", "返品"]]

    if not target_rows:
        st.warning("状態変更できる在庫がありません。")
    else:
        options = [
            f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["重量kg"]}kg / {r["状態"]} / {r["保管場所"]}'
            for r in target_rows
        ]

        selected = st.selectbox("状態変更する在庫を選択", options)
        source = target_rows[options.index(selected)]

        st.subheader("現在の情報")
        st.table([
            {"項目": "在庫ID", "内容": source["在庫単位ID"]},
            {"項目": "取引先", "内容": source["取引先"]},
            {"項目": "樹脂", "内容": source["樹脂"]},
            {"項目": "重量kg", "内容": source["重量kg"]},
            {"項目": "現在状態", "内容": source["状態"]},
            {"項目": "保管場所", "内容": source["保管場所"]},
        ])

        new_status = st.selectbox("変更後の状態", ["誤登録", "廃棄", "返品"])
        note = st.text_area("理由・備考")

        if st.button("状態変更実行"):
            if not note:
                st.error("理由・備考を入力してください。")
            else:
                old_status = source["状態"]

                update_inventory_status(
                    source["在庫単位ID"],
                    new_status,
                    st.session_state.username
                )

                insert_history(
                    source["在庫単位ID"],
                    "状態変更",
                    f"{old_status} → {new_status} / {note}"
                )

                st.success(f"{source['在庫単位ID']} を {new_status} に変更しました。")

# ==========================
# ラベル印刷（専用）
# ==========================
elif menu == "ラベル印刷":
    st.header("ラベル印刷（専用）")

    rows = get_inventory_rows()

    active_rows = [r for r in rows if r["状態"] not in ["出荷済", "誤登録", "廃棄", "返品"]]

    if not active_rows:
        st.warning("在庫がありません")
    else:
        options = [
            f'{r["在庫単位ID"]} / {r["取引先"]} / {r["樹脂"]} / {r["重量kg"]}kg'
            for r in active_rows
        ]

        selected = st.multiselect("印刷する在庫を選択", options)

        selected_rows = []
        for item in selected:
            selected_rows.append(active_rows[options.index(item)])

        st.write(f"選択中：{len(selected_rows)}件")

        if selected_rows:
            html = """
            <html>
            <head>
            <meta charset="utf-8">
            <style>
            @page {
                size: A4 portrait;
                margin: 15mm;
            }

            body {
                font-family: Arial, sans-serif;
                margin: 0;
            }

            .label {
                width: 100%;
                height: 250mm;
                border: 4px solid black;
                padding: 20mm;
                box-sizing: border-box;
                page-break-after: always;
            }

            .label-id {
                font-size: 72px;
                font-weight: bold;
                margin-bottom: 20mm;
            }

            .label-main {
                font-size: 42px;
                font-weight: bold;
                margin-bottom: 12mm;
            }

            .label-sub {
                font-size: 32px;
                margin-bottom: 8mm;
            }
            </style>
            </head>
            <body>
            """

            for r in selected_rows:
                html += f"""
                <div class="label">
                    <div class="label-id">{r["在庫単位ID"]}</div>
                    <div class="label-main">{r["取引先"]} / {r["樹脂"]}</div>
                    <div class="label-sub">色：{r["色"]}</div>
                    <div class="label-sub">形状：{r["形状"]}</div>
                    <div class="label-sub">重量：{r["重量kg"]} kg</div>
                    <div class="label-sub">場所：{r["保管場所"]}</div>
                </div>
                """

            html += """
            </body>
            </html>
            """

            # 💡 クラウド・サーバー環境へのデプロイを見据え、ローカルでブラウザを開く仕様から、
            # ブラウザ経由で「印刷用HTML」を直接ダウンロードさせる仕様に安全化しました。
            st.success("印刷用データが生成されました。下のボタンから取得して印刷してください。")
            st.download_button(
                label="🖨️ 印刷用HTMLをダウンロード",
                data=html,
                file_name=f"labels_{datetime.now().strftime('%Y%m%d%H%M%S')}.html",
                mime="text/html"
            )

# =========================
# 履歴一覧
# =========================
elif menu == "履歴一覧":

    st.header("履歴一覧")

    history_rows = get_history_rows()

    if history_rows:
        st.dataframe(history_rows, use_container_width=True)
    else:
        st.write("履歴はありません。")

# ==========================
# バックアップ
# ==========================
elif menu == "バックアップ":
    st.header("バックアップ")

    st.write("現在のSQLiteデータベースをバックアップします。")

    if st.button("バックアップ作成"):
        backup_dir = "backups"

        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/inventory_backup_{timestamp}.db"

        shutil.copy("inventory.db", backup_file)

        st.success("バックアップを作成しました。")
        st.write(backup_file)

# ==========================
# マスタ管理
# ==========================
elif menu == "マスタ管理":
    st.header("マスタ管理")

    categories = {
        "樹脂": "materials",
        "色": "colors",
        "形状": "shapes",
        "荷姿": "packages",
        "保管場所": "locations",
        "取引先": "customers",
    }

    selected_label = st.selectbox("マスタ種別", list(categories.keys()))
    selected_category = categories[selected_label]

    st.subheader(f"{selected_label} の追加")

    new_name = st.text_input("追加する名称")

    if st.button("追加"):
        if not new_name:
            st.error("名称を入力してください。")
        else:
            insert_master_item(selected_category, new_name)
            st.success(f"{selected_label} に {new_name} を追加しました。")

    st.subheader(f"{selected_label} 一覧")

    items = get_master_items_with_order(selected_category)

    if items:
        order_dict = {}

        for item in items:
            name = item["name"]
            current_order = int(item["sort_order"] or ((items.index(item) + 1) * 10))

            col1, col2, col3 = st.columns([4, 2, 2])

            with col1:
                st.write(name)

            with col2:
                order = st.number_input(
                    "表示順",
                    value=current_order,
                    step=10,
                    key=f"{selected_category}_{name}_order"
                )

            order_dict[name] = order

            with col3:
                if st.button("無効化", key=f"delete_{selected_category}_{name}"):
                    deactivate_master_item(selected_category, name)
                    st.success(f"{name} を無効化しました。")

        if st.button("表示順を一括保存"):
            update_master_sort_orders(selected_category, order_dict)
            st.success("表示順を保存しました。画面を更新してください。")

        if len(set(order_dict.values())) != len(order_dict):
            st.error("表示順が重複しています。")

# ==========================
# 加工ロット一覧
# ==========================
elif menu == "加工ロット一覧":  # 💡 正しい多重分岐（else の手前）の階層に修正しました

    st.header("加工ロット一覧")

    lots = get_process_lots()

    if lots:
        st.dataframe(lots, use_container_width=True)
    else:
        st.info("加工ロットはありません。")

# ==========================
# QRコード生成（Phase 5）
# ==========================
elif menu == "QRコード生成":

    st.header("QRコード生成")

    st.subheader("在庫単位のQRコード生成")

    # 在庫一覧から選択
    inventory_rows = get_inventory_rows()

    if inventory_rows:
        unit_ids = [row["在庫単位ID"] for row in inventory_rows]

        selected_unit_id = st.selectbox("在庫単位IDを選択", unit_ids)

        if st.button("QRコード生成"):
            try:
                # QRコードを生成
                qrcode_data = QRCodeService.generate_qrcode(selected_unit_id)

                # QRコード情報を保存
                result = QRCodeService.save_qrcode_map(
                    selected_unit_id,
                    qrcode_data,
                    qrcode_url=""
                )

                if result['success']:
                    st.success(result['message'])

                    # QRコードを表示
                    st.subheader("生成されたQRコード")

                    # HTMLで表示
                    html_img = QRCodeService.get_qrcode_html(selected_unit_id, size="300px")
                    st.markdown(html_img, unsafe_allow_html=True)

                    # ダウンロードボタン
                    qrcode_info = QRCodeService.get_qrcode(selected_unit_id)

                    if qrcode_info:
                        import base64
                        import io
                        from PIL import Image

                        # Base64をデコードしてPNG化
                        qrcode_bytes = base64.b64decode(qrcode_info['qrcode_data'])

                        st.download_button(
                            label="QRコードをダウンロード",
                            data=qrcode_bytes,
                            file_name=f"qrcode_{selected_unit_id}.png",
                            mime="image/png"
                        )

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=st.session_state.username,
                        action="GENERATE_QRCODE",
                        table_name="qrcode_map",
                        record_id=selected_unit_id,
                        detail=f"QRコードを生成しました：{selected_unit_id}"
                    )

                else:
                    st.error(result['message'])

            except Exception as e:
                st.error(f"エラー：{str(e)}")

                # エラーログを記録
                AuditLogService.log_error(
                    username=st.session_state.username,
                    action="GENERATE_QRCODE",
                    error_message=str(e)
                )

    else:
        st.info("在庫がありません。")

# ==========================
# ユーザー管理（Phase 5）
# ==========================
elif menu == "ユーザー管理":

    st.header("ユーザー管理")

    tab1, tab2 = st.tabs(["ユーザー作成", "ロール管理"])

    with tab1:
        st.subheader("新規ユーザー作成")

        new_username = st.text_input("ユーザー名", key="admin_new_user")
        new_password = st.text_input("パスワード", type="password", key="admin_new_pass")
        new_full_name = st.text_input("フルネーム", key="admin_full_name")
        new_email = st.text_input("メールアドレス", key="admin_email")

        if st.button("ユーザー作成", key="admin_create_user"):
            if not new_username:
                st.error("ユーザー名を入力してください")
            elif len(new_password) < 6:
                st.error("パスワードは6文字以上です")
            else:
                result = AuthService.register_user(
                    new_username,
                    new_password,
                    new_full_name,
                    new_email
                )

                if result['success']:
                    st.success(result['message'])

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=st.session_state.username,
                        action="CREATE_USER",
                        table_name="users",
                        record_id=new_username,
                        detail=f"ユーザーを作成しました：{new_username}"
                    )

                else:
                    st.error(result['message'])

    with tab2:
        st.subheader("ロール割り当て")

        # ユーザーリストを取得（簡易実装：DBから直接取得）
        from db import get_conn

        with get_conn() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cur = conn.cursor()

            cur.execute("SELECT username, full_name FROM users WHERE is_active = 1")
            users = cur.fetchall()

        if users:
            user_options = {u['full_name']: u['username'] for u in users}

            selected_user = st.selectbox("ユーザーを選択", list(user_options.keys()))
            selected_username = user_options[selected_user]

            roles = ["受取", "検査", "加工", "出荷", "管理", "admin"]

            selected_role = st.selectbox("ロールを選択", roles)

            if st.button("ロール割り当て"):
                result = AuthService.assign_role(selected_username, selected_role)

                if result['success']:
                    st.success(result['message'])

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=st.session_state.username,
                        action="ASSIGN_ROLE",
                        table_name="user_roles",
                        record_id=selected_username,
                        detail=f"ロールを割り当てました：{selected_username} = {selected_role}"
                    )

                else:
                    st.error(result['message'])

            # 現在のロール表示
            st.subheader(f"{selected_user} のロール")

            current_roles = AuthService.get_user_roles(selected_username)

            if current_roles:
                st.write(", ".join(current_roles))
            else:
                st.info("ロールが割り当てられていません")

        else:
            st.info("ユーザーがありません。")

# ==========================
# 監査ログ（Phase 5）
# ==========================
elif menu == "監査ログ":

    st.header("監査ログ")

    tab1, tab2 = st.tabs(["操作ログ", "統計"])

    with tab1:
        st.subheader("操作ログ一覧")

        col1, col2 = st.columns(2)

        with col1:
            filter_username = st.text_input("ユーザー名でフィルタ（空白で全て）", key="audit_username")

        with col2:
            filter_action = st.text_input("アクション（空白で全て）", key="audit_action")

        if st.button("検索"):
            logs = AuditLogService.get_audit_logs(
                username=filter_username if filter_username else "",
                action=filter_action if filter_action else "",
                limit=200
            )

            if logs:
                st.dataframe(logs, use_container_width=True)
            else:
                st.info("ログがありません。")

    with tab2:
        st.subheader("操作統計")

        days = st.slider("過去N日間", 1, 90, 30)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("操作別集計")

            summary = AuditLogService.get_action_summary(days=days)

            if summary:
                st.dataframe(summary, use_container_width=True)

        with col2:
            st.subheader("エラー統計")

            error_count = AuditLogService.get_error_count(days=days)

            st.metric("エラー件数", error_count)

# ==========================
# ユーザー設定（Phase 5.1）
# ==========================
elif menu == "⚙️ ユーザー設定":

    st.header("ユーザー設定")

    tab1, tab2 = st.tabs(["パスワード変更", "プロフィール編集"])

    with tab1:
        st.subheader("パスワード変更")

        # 現在のユーザー情報を取得
        current_user = AuthService.get_user(st.session_state.username)

        if current_user:
            st.write(f"ユーザー名: **{current_user['username']}**")
            st.write(f"フルネーム: {current_user['full_name']}")

        st.divider()

        old_password = st.text_input("現在のパスワード", type="password", key="old_pass")
        new_password = st.text_input("新しいパスワード", type="password", key="new_pass")
        new_password_confirm = st.text_input("新しいパスワード（再入力）", type="password", key="new_pass_confirm")

        if st.button("パスワードを変更"):
            if not old_password:
                st.error("現在のパスワードを入力してください")
            elif len(new_password) < 6:
                st.error("新しいパスワードは6文字以上です")
            elif new_password != new_password_confirm:
                st.error("新しいパスワードが一致しません")
            else:
                result = AuthService.change_password(
                    st.session_state.username,
                    old_password,
                    new_password
                )

                if result['success']:
                    st.success(result['message'])

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=st.session_state.username,
                        action="CHANGE_PASSWORD",
                        table_name="users",
                        record_id=st.session_state.username,
                        detail="パスワードを変更しました"
                    )

                else:
                    st.error(result['message'])

                    # エラーログを記録
                    AuditLogService.log_error(
                        username=st.session_state.username,
                        action="CHANGE_PASSWORD",
                        error_message=result['message']
                    )

    with tab2:
        st.subheader("プロフィール編集")

        # 現在のユーザー情報を取得
        current_user = AuthService.get_user(st.session_state.username)

        if current_user:
            full_name = st.text_input("フルネーム", value=current_user['full_name'], key="edit_full_name")
            email = st.text_input("メールアドレス", value=current_user['email'] or "", key="edit_email")

            if st.button("プロフィールを更新"):
                result = AuthService.update_user_info(
                    st.session_state.username,
                    full_name=full_name,
                    email=email
                )

                if result['success']:
                    st.success(result['message'])

                    # セッション状態を更新
                    updated_user = AuthService.get_user(st.session_state.username)
                    st.session_state.user_info = updated_user

                    # 監査ログを記録
                    AuditLogService.log_action(
                        username=st.session_state.username,
                        action="UPDATE_PROFILE",
                        table_name="users",
                        record_id=st.session_state.username,
                        detail=f"プロフィールを更新しました（フルネーム: {full_name}）"
                    )

                    st.rerun()

                else:
                    st.error(result['message'])

        else:
            st.error("ユーザー情報を取得できません")

else:  # 💡 すべてのメニュー条件から外れた際のセーフティガードとして最下部に配置
    st.write("メニューを選択してください。")