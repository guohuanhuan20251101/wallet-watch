"""
可编辑交易表格 + 批量修改组件
"""
import streamlit as st
import pandas as pd
from app.db.models import get_session, FactTransaction, DimCategory, DimSource


def get_all_categories() -> list[str]:
    """获取所有类别名称列表"""
    session = get_session()
    try:
        return sorted([c.category_name for c in session.query(DimCategory).all()])
    finally:
        session.close()


def render_editable_table(
    df: pd.DataFrame,
    key_prefix: str,
    title: str = "交易记录",
    max_rows: int = 50,
    show_source: bool = True,
):
    """
    可编辑的交易表格组件
    - 默认显示模式，右上角有 ✏️ 编辑按钮
    - 点击后切换到编辑模式，可直接在表内修改类别和类型
    - 只保存被修改的行

    要求 df 包含列: transaction_id, date, amount, merchant, category, source, transaction_type
    """
    if df.empty:
        st.info("暂无数据")
        return

    all_cats = get_all_categories()

    # ── 标题行 + 编辑按钮 ──
    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.markdown(f'<p class="section-title">{title}</p>', unsafe_allow_html=True)

    edit_key = f"{key_prefix}_edit_mode"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False

    with col_btn:
        if st.session_state[edit_key]:
            if st.button("🔒 退出编辑", key=f"{key_prefix}_exit", use_container_width=True):
                st.session_state[edit_key] = False
                st.rerun()
        else:
            if st.button("✏️ 编辑", key=f"{key_prefix}_enter", use_container_width=True):
                st.session_state[edit_key] = True
                st.rerun()

    # ── 限制显示行数 ──
    display_df = df.head(max_rows).copy()

    if not st.session_state[edit_key]:
        # ── 显示模式：好看的静态表格 ──
        rows_html = ""
        for _, row in display_df.iterrows():
            src_cls = "wechat" if str(row["source"]) == "微信" else "alipay"
            amt_cls = "amount-expense" if row["transaction_type"] == "支出" else "amount-income"
            rows_html += f"""
            <tr>
                <td>{row['date']}</td>
                <td>{row['merchant']}</td>
                <td><span class="badge">{row['category']}</span></td>
                <td class="{amt_cls}">¥{row['amount']:.2f}</td>
                <td><span class="badge {src_cls}">{row['source']}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class="styled-table">
            <thead><tr>
                <th>日期</th><th>商户</th><th>类别</th><th>金额</th><th>来源</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

    else:
        # ── 编辑模式：st.data_editor ──
        edit_cols = ["date", "merchant", "amount", "category", "transaction_type"]
        if show_source:
            edit_cols.insert(4, "source")

        editor_df = display_df[edit_cols].copy()
        editor_df.rename(columns={
            "date": "日期",
            "merchant": "商户",
            "amount": "金额",
            "source": "来源",
            "category": "类别",
            "transaction_type": "类型",
        }, inplace=True)

        # 加回 transaction_id 用于后续保存
        editor_df["_tid"] = display_df["transaction_id"].values

        edited = st.data_editor(
            editor_df,
            column_config={
                "日期": st.column_config.TextColumn(disabled=True),
                "商户": st.column_config.TextColumn(disabled=True),
                "金额": st.column_config.NumberColumn(disabled=True, format="¥%.2f"),
                "来源": st.column_config.TextColumn(disabled=True),
                "类别": st.column_config.SelectboxColumn(
                    options=all_cats,
                    required=True,
                ),
                "类型": st.column_config.SelectboxColumn(
                    options=["支出", "收入"],
                    required=True,
                ),
                "_tid": None,  # 隐藏
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=f"{key_prefix}_editor",
        )

        if st.button("💾 保存修改", key=f"{key_prefix}_save", type="primary"):
            changed = 0
            for i, row in edited.iterrows():
                orig = editor_df.iloc[i]
                if row["类别"] != orig["类别"] or row["类型"] != orig["类型"]:
                    tid = int(orig["_tid"])
                    _update_transaction(tid, row["类别"], row["类型"])
                    changed += 1

            if changed > 0:
                st.cache_data.clear()
                st.success(f"✅ 已保存 {changed} 条修改，刷新页面即可生效")
                st.session_state[edit_key] = False
                st.rerun()
            else:
                st.info("没有检测到修改")


def render_bulk_editor(df: pd.DataFrame):
    """
    批量修改组件：按条件筛选，一次性修改一大类记录
    """
    if df.empty:
        return

    st.markdown('<p class="section-title">📦 批量修改分类</p>', unsafe_allow_html=True)
    st.caption("适用于：想一次性改一大类订单（比如京东全部从「购物」改为「美食」）")

    all_cats = get_all_categories()

    col1, col2, col3 = st.columns(3)
    with col1:
        sources = ["全部"] + sorted(df["source"].unique().tolist())
        filter_source = st.selectbox("筛选来源", sources, key="bulk_source")
    with col2:
        cats = ["全部"] + all_cats
        filter_cat = st.selectbox("当前类别", cats, key="bulk_old_cat")
    with col3:
        keyword = st.text_input("🔍 商户关键字（可选）", key="bulk_keyword",
                                placeholder="例如：京东")

    # ── 应用筛选 ──
    matched = df.copy()
    if filter_source != "全部":
        matched = matched[matched["source"] == filter_source]
    if filter_cat != "全部":
        matched = matched[matched["category"] == filter_cat]
    if keyword.strip():
        matched = matched[matched["merchant"].astype(str).str.contains(
            keyword.strip(), case=False, na=False
        )]

    st.caption(f"匹配 **{len(matched)}** 条记录（共 {len(df)} 条）")

    if matched.empty:
        st.warning("没有匹配的记录")
        return

    # ── 预览匹配结果 ──
    with st.expander(f"📋 预览匹配的 {min(len(matched), 20)} 条记录", expanded=(len(matched) <= 10)):
        preview = matched[["date", "merchant", "category", "amount", "source"]].head(20)
        preview["date"] = preview["date"].astype(str)
        st.dataframe(preview, use_container_width=True, hide_index=True)

    # ── 设置目标值 ──
    col_a, col_b = st.columns(2)
    with col_a:
        new_cat = st.selectbox("改为类别", all_cats, key="bulk_new_cat")
    with col_b:
        new_type = st.selectbox("改为类型", ["不修改", "支出", "收入"], key="bulk_new_type")

    if st.button("🚀 批量修改", type="primary", use_container_width=True, key="bulk_apply"):
        changed = 0
        for _, row in matched.iterrows():
            tid = int(row["transaction_id"])
            type_to_set = row["transaction_type"] if new_type == "不修改" else new_type
            _update_transaction(tid, new_cat, type_to_set)
            changed += 1

        st.cache_data.clear()
        st.success(f"✅ 已批量修改 {changed} 条记录，刷新页面即可生效")
        st.rerun()


def _update_transaction(transaction_id: int, new_category: str, new_type: str):
    """更新单条交易的分类和类型"""
    session = get_session()
    try:
        cat = session.query(DimCategory).filter_by(category_name=new_category).first()
        txn = session.query(FactTransaction).filter_by(transaction_id=transaction_id).first()
        if txn and cat:
            txn.category_id = cat.category_id
            txn.transaction_type = new_type
            session.commit()
    finally:
        session.close()
